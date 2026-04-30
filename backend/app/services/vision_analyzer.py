"""Combined animal vision analysis using a single Groq multimodal call."""

import base64
import io
import json
import logging

import httpx
from PIL import Image

from app.config import get_settings
from app.services.groq_retry import groq_post_with_retry

logger = logging.getLogger(__name__)

VISION_PROMPT = """You are a veterinary AI assistant analyzing animals for a rescue-support app.

Analyze this image in ONE pass and respond ONLY with valid JSON in this exact shape:
{
  "dog_detected": true,
  "species": "dog",
  "dog_confidence": 0.95,
  "dog_description": "brief description of what animal is visible",
  "emotion": {
    "label": "happy",
    "confidence": 0.85,
    "description": "brief explanation of the dog's emotional state"
  },
  "condition": {
    "breed_guess": "best guess of breed/species type, or 'Indian pariah / mixed breed' for unclear dogs",
    "estimated_age": "puppy / young adult / adult / senior",
    "physical_condition": "one paragraph describing overall physical condition",
    "visible_injuries": ["list of visible injuries, wounds, or physical problems"],
    "health_concerns": ["list of likely health concerns like mange, malnutrition, ticks, maggots, eye infection, etc."],
    "body_language": "description of posture, tail, ears, and overall body language"
  },
  "urgency_signals": ["visible or context-provided emergency clues"],
  "unknown_factors": ["important facts that cannot be determined from image/context"],
  "scenario_type": "short snake_case label such as fall_entrapment, road_trauma, heatstroke, skin_disease, cat_urinary_obstruction, cow_bloat, healthy_or_low_risk, no_dog_visible, unclear"
}

Rules:
- First decide which species is visible. species must be exactly one of: dog, cat, cow, other.
- Keep "dog_detected" true for dog, cat, and cow because the existing app field means a supported animal was detected.
- If no supported animal is visible, set "dog_detected" to false, species to "other", and use:
  - "dog_confidence": a number between 0 and 1
  - "dog_description": what is visible instead
  - "emotion": {"label": "unknown", "confidence": 0.0, "description": "No dog visible"}
  - "condition": {
      "breed_guess": "Unable to determine (no dog visible)",
      "estimated_age": "Unknown",
      "physical_condition": "No supported animal was visible in the image.",
      "visible_injuries": [],
      "health_concerns": [],
      "body_language": "No supported animal visible"
    }
  - "urgency_signals": []
  - "unknown_factors": ["dog_not_visible"]
  - "scenario_type": "no_dog_visible"
- Emotion label must be exactly one of: happy, sad, angry, relaxed, fearful, unknown
- For cats, avoid dog body-language assumptions. For cows/cattle/buffalo/calves, keep advice conservative and livestock-oriented.
- Distinguish clearly between what is directly visible and what is only a likely possibility
- Treat user-provided context as important scene information, but do not invent visual findings from it
- Be cautious when identifying health issues and avoid overclaiming from limited visual evidence
- Do not wrap the JSON in markdown
"""

VALID_EMOTIONS = {"happy", "sad", "angry", "relaxed", "fearful", "unknown"}


def _default_condition() -> dict:
    return {
        "breed_guess": "Unable to determine (analysis unavailable)",
        "estimated_age": "Unknown",
        "physical_condition": "Could not analyze - please consult a veterinarian.",
        "visible_injuries": [],
        "health_concerns": [],
        "body_language": "Could not analyze",
    }


def unavailable_result() -> dict:
    """Contract payload for cases where the vision model cannot run."""
    return {
        "dog_detected": False,
        "analysis_status": "unavailable",
        "species": "other",
        "dog_confidence": 0.0,
        "dog_description": "Analysis unavailable",
        "emotion": {
            "label": "unknown",
            "confidence": 0.0,
            "description": "Analysis unavailable",
        },
        "condition": _default_condition(),
        "urgency_signals": [],
        "unknown_factors": ["analysis_unavailable"],
        "scenario_type": "analysis_unavailable",
    }


def _strip_code_fences(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    return text.strip()


def _extract_json_object(content: str) -> str:
    text = _strip_code_fences(content)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def _normalize_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        if isinstance(item, str):
            cleaned = item.strip()
            if cleaned:
                items.append(cleaned)
    return items


def _normalize_confidence(value: object, default: float) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, round(confidence, 3)))


def _normalize_result(payload: dict) -> dict:
    dog_detected = bool(payload.get("dog_detected"))
    species = str(payload.get("species") or ("dog" if dog_detected else "other")).strip().lower()
    species = {
        "kitten": "cat",
        "feline": "cat",
        "cattle": "cow",
        "calf": "cow",
        "buffalo": "cow",
        "bull": "cow",
        "heifer": "cow",
    }.get(species, species)
    if species not in {"dog", "cat", "cow", "other"}:
        species = "dog" if dog_detected else "other"
    emotion_payload = payload.get("emotion") if isinstance(payload.get("emotion"), dict) else {}
    condition_payload = payload.get("condition") if isinstance(payload.get("condition"), dict) else {}

    label = str(emotion_payload.get("label", "unknown")).strip().lower()
    if label not in VALID_EMOTIONS:
        label = "unknown"

    condition = {
        "breed_guess": str(condition_payload.get("breed_guess") or _default_condition()["breed_guess"]).strip(),
        "estimated_age": str(condition_payload.get("estimated_age") or _default_condition()["estimated_age"]).strip(),
        "physical_condition": str(
            condition_payload.get("physical_condition") or _default_condition()["physical_condition"]
        ).strip(),
        "visible_injuries": _normalize_string_list(condition_payload.get("visible_injuries")),
        "health_concerns": _normalize_string_list(condition_payload.get("health_concerns")),
        "body_language": str(condition_payload.get("body_language") or _default_condition()["body_language"]).strip(),
    }

    analysis_status = str(payload.get("analysis_status") or "").strip().lower()
    if analysis_status not in {"complete", "uncertain", "no_dog_visible", "unavailable"}:
        analysis_status = "complete" if dog_detected else "no_dog_visible"

    if not dog_detected:
        condition = {
            "breed_guess": "Unable to determine (no dog visible)",
            "estimated_age": "Unknown",
            "physical_condition": "No dog was visible in the image.",
            "visible_injuries": [],
            "health_concerns": [],
            "body_language": "No dog visible",
        }
        species = "other"

    return {
        "dog_detected": dog_detected,
        "analysis_status": analysis_status,
        "species": species,
        "dog_confidence": _normalize_confidence(payload.get("dog_confidence"), 0.0),
        "dog_description": str(payload.get("dog_description", "")).strip(),
        "emotion": {
            "label": label if dog_detected else "unknown",
            "confidence": _normalize_confidence(emotion_payload.get("confidence"), 0.0 if not dog_detected else 0.5),
            "description": str(emotion_payload.get("description") or "Could not determine emotion").strip(),
        },
        "condition": condition,
        "urgency_signals": _normalize_string_list(payload.get("urgency_signals")),
        "unknown_factors": _normalize_string_list(payload.get("unknown_factors")),
        "scenario_type": str(
            payload.get("scenario_type") or ("unclear" if dog_detected else "no_dog_visible")
        ).strip().lower().replace(" ", "_"),
    }


async def analyze_vision(image_bytes: bytes, user_context: str | None = None) -> dict | None:
    """Analyze dog presence, emotion, and condition in one call."""
    settings = get_settings()
    if not settings.groq_api_key:
        logger.warning("Groq API key not configured, skipping combined vision analysis.")
        return unavailable_result()

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=85)
    b64_image = base64.b64encode(buf.getvalue()).decode("utf-8")

    prompt = VISION_PROMPT
    if user_context and user_context.strip():
        prompt = f"{VISION_PROMPT}\n\nUser-provided context: {user_context.strip()[:1000]}"

    try:
        async with httpx.AsyncClient(timeout=40.0) as client:
            response = await groq_post_with_retry(
                client,
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json_body={
                    "model": settings.groq_vision_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{b64_image}"
                                    },
                                },
                            ],
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1000,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return _normalize_result(json.loads(_extract_json_object(content)))
    except Exception as exc:
        logger.error(f"Combined vision analysis failed: {exc}")
        return None
