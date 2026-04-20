"""Condition analyzer using multimodal VLM (Groq free tier).

Sends the dog image to a vision-language model and asks for a structured
assessment of the dog's physical condition, injuries, breed, and health.

Primary: Groq API (llama-3.2-90b-vision-preview)
Fallback: HuggingFace Inference API
"""

import base64
import io
import json
import logging
import httpx
from PIL import Image

from app.config import get_settings

logger = logging.getLogger(__name__)

CONDITION_PROMPT = """You are a veterinary AI assistant. Analyze this image of a dog and provide a structured assessment. Be thorough but compassionate.

Respond ONLY with valid JSON in this exact format:
{
  "breed_guess": "best guess of breed or mix, or 'Indian pariah / mixed breed' if unclear",
  "estimated_age": "puppy / young adult / adult / senior",
  "physical_condition": "one paragraph describing overall physical condition",
  "visible_injuries": ["list of any visible injuries, wounds, or physical problems"],
  "health_concerns": ["list of health concerns like mange, malnutrition, ticks, eye infection, etc."],
  "body_language": "description of the dog's posture, tail, ears, and overall body language"
}

If you cannot identify specific details, make your best assessment and note uncertainty. Always err on the side of caution for safety."""


async def analyze_condition_groq(image_bytes: bytes) -> dict | None:
    """Analyze dog condition using Groq vision API."""
    settings = get_settings()
    if not settings.groq_api_key:
        logger.warning("Groq API key not configured, skipping VLM analysis.")
        return None

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=85)
    b64_image = base64.b64encode(buf.getvalue()).decode("utf-8")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.groq_vision_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": CONDITION_PROMPT},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{b64_image}"
                                    },
                                },
                            ],
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 800,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Extract JSON from response (model may wrap in markdown)
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                content = content.rsplit("```", 1)[0]

            return json.loads(content)

    except httpx.HTTPStatusError as e:
        logger.error(f"Groq API error: {e.response.status_code} — {e.response.text}")
        return None
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse VLM response: {e}")
        return None
    except Exception as e:
        logger.error(f"Condition analysis failed: {e}")
        return None


async def analyze_condition_hf(image_bytes: bytes) -> dict | None:
    """Fallback: analyze dog condition using HuggingFace Inference API."""
    settings = get_settings()
    if not settings.hf_api_token:
        logger.warning("HF API token not configured, skipping fallback.")
        return None

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=85)
    b64_image = base64.b64encode(buf.getvalue()).decode("utf-8")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api-inference.huggingface.co/models/Salesforce/blip2-opt-2.7b",
                headers={"Authorization": f"Bearer {settings.hf_api_token}"},
                json={
                    "inputs": {
                        "image": b64_image,
                        "text": "Describe this dog's physical condition, breed, injuries, and body language in detail.",
                    }
                },
            )
            response.raise_for_status()
            data = response.json()

            # HF returns a text description, not structured JSON
            description = data[0].get("generated_text", "") if isinstance(data, list) else str(data)

            return {
                "breed_guess": "Unable to determine precisely",
                "estimated_age": "Unknown",
                "physical_condition": description,
                "visible_injuries": [],
                "health_concerns": [],
                "body_language": "See physical condition description",
            }
    except Exception as e:
        logger.error(f"HF fallback analysis failed: {e}")
        return None


async def analyze_condition(image_bytes: bytes) -> dict:
    """Analyze dog condition with Groq primary, HF fallback.

    Always returns a dict (possibly with defaults if both fail).
    """
    result = await analyze_condition_groq(image_bytes)
    if result:
        return result

    result = await analyze_condition_hf(image_bytes)
    if result:
        return result

    # Last resort defaults
    return {
        "breed_guess": "Unable to determine (analysis unavailable)",
        "estimated_age": "Unknown",
        "physical_condition": "Could not analyze — please consult a veterinarian.",
        "visible_injuries": [],
        "health_concerns": [],
        "body_language": "Could not analyze",
    }
