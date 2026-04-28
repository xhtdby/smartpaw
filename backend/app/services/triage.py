"""Fast situational triage for first-aid chat turns."""

from __future__ import annotations

import json
import logging
import re

import httpx
from pydantic import BaseModel, Field

from app.config import get_settings
from app.services.groq_retry import groq_post_with_retry

logger = logging.getLogger(__name__)

URGENCY_TIERS = {"life_threatening", "urgent", "moderate", "low_risk", "unclear"}
LOCAL_DECISION_SCENARIOS = {
    "fall_entrapment",
    "choking_airway",
    "seizure_collapse",
    "severe_bleeding",
    "heatstroke",
    "road_trauma",
    "poisoning",
    "maggot_wound",
    "skin_disease",
    "puppy_gi",
    "eye_injury",
    "fearful_aggressive",
    "rabies_exposure",
    "healthy_or_low_risk",
    "lost_dog",
    "feeding_weak_dog",
    "routine_care",
    "tick_infestation",
    "vomiting_diarrhea",
    "burn_injury",
    "unsafe_medicine",
    "unsafe_home_remedy",
    "injured_transport",
    "no_dog_visible",
}


class TriageResult(BaseModel):
    urgency_tier: str = "unclear"
    info_sufficient: bool = False
    missing_facts: list[str] = Field(default_factory=list)
    scenario_type: str = "unclear"
    needs_helpline_first: bool = False
    rationale: str = ""


TRIAGE_SYSTEM_PROMPT = """You classify urgent dog rescue / first-aid chat messages.

Return ONLY valid JSON:
{
  "urgency_tier": "life_threatening" | "urgent" | "moderate" | "low_risk" | "unclear",
  "info_sufficient": true | false,
  "missing_facts": ["short_snake_case_fact"],
  "scenario_type": "short_snake_case",
  "needs_helpline_first": true | false,
  "rationale": "one short line"
}

Rules:
- Mark life_threatening for entrapment in wells/pits/drains, drowning, choking, not breathing, collapse, repeated seizure, heavy bleeding, heatstroke collapse, major road trauma, suspected spinal injury, severe poisoning signs.
- Mark needs_helpline_first true when the scene needs rescue equipment or urgent dispatch: well/pit/drain/pipe entrapment, drowning, major road accident, trapped under vehicle, roof/height rescue, aggressive dog endangering people.
- If the message is vague ("acting weird", "not ok", "help") and no analysis context gives specifics, set info_sufficient false and ask for the few missing facts needed to choose safe first aid.
- Do not make info_sufficient false just because the city, exact age, or depth is unknown when the immediate hazard is already clear.
- scenario_type examples: fall_entrapment, choking_airway, poisoning, heatstroke, road_trauma, fracture, severe_bleeding, seizure_collapse, maggot_wound, skin_disease, puppy_gi, eye_injury, fearful_aggressive, healthy_or_low_risk, no_dog_visible, unclear.
"""


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


def _normalize_string_list(value: object, limit: int = 5) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        if isinstance(item, str):
            cleaned = re.sub(r"[^a-z0-9_]+", "_", item.strip().lower()).strip("_")
            if cleaned:
                items.append(cleaned)
    return items[:limit]


def _normalize_result(raw: dict | None, fallback: TriageResult) -> TriageResult:
    if not isinstance(raw, dict):
        return fallback

    urgency_tier = str(raw.get("urgency_tier", fallback.urgency_tier)).strip().lower()
    if urgency_tier not in URGENCY_TIERS:
        urgency_tier = fallback.urgency_tier

    scenario_type = re.sub(
        r"[^a-z0-9_]+",
        "_",
        str(raw.get("scenario_type", fallback.scenario_type)).strip().lower(),
    ).strip("_") or fallback.scenario_type

    return TriageResult(
        urgency_tier=urgency_tier,
        info_sufficient=bool(raw.get("info_sufficient", fallback.info_sufficient)),
        missing_facts=_normalize_string_list(raw.get("missing_facts")) or fallback.missing_facts,
        scenario_type=scenario_type,
        needs_helpline_first=bool(raw.get("needs_helpline_first", fallback.needs_helpline_first)),
        rationale=str(raw.get("rationale", fallback.rationale)).strip()[:220],
    )


def _contains_any(text: str, patterns: list[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def heuristic_classify_situation(
    user_message: str,
    analysis_context: str | None = None,
    last_assistant_message: str | None = None,
) -> TriageResult:
    """Deterministic fallback used when the model is unavailable."""
    combined = " ".join(
        part for part in [user_message, analysis_context or "", last_assistant_message or ""] if part
    ).lower()
    compact = re.sub(r"\s+", " ", combined).strip()

    if not compact:
        return TriageResult(
            info_sufficient=False,
            missing_facts=["what_happened", "current_symptoms"],
            rationale="No situation details were provided.",
        )

    vague_only = (
        len(compact.split()) <= 8
        and _contains_any(compact, ["acting weird", "weird", "sick", "not ok", "help", "unwell"])
        and not _contains_any(
            compact,
            [
                "well",
                "pit",
                "bleeding",
                "blood",
                "choking",
                "poison",
                "seizure",
                "collapse",
                "hit",
                "accident",
                "heat",
                "maggot",
                "diarrhea",
                "vomit",
            ],
        )
    )
    if vague_only:
        return TriageResult(
            urgency_tier="unclear",
            info_sufficient=False,
            missing_facts=["main_symptom", "breathing_and_responsiveness", "recent_event_or_exposure"],
            scenario_type="unclear",
            rationale="The message is too vague to choose safe first aid.",
        )

    if _contains_any(compact, ["no dog", "dog is not visible", "no animal visible"]):
        return TriageResult(
            urgency_tier="low_risk",
            info_sufficient=True,
            scenario_type="no_dog_visible",
            rationale="The user says there is no visible dog to assess.",
        )

    if _contains_any(
        compact,
        ["paracetamol", "acetaminophen", "ibuprofen", "aspirin", "painkiller", "pain killer", "human medicine"],
    ):
        return TriageResult(
            urgency_tier="urgent" if _contains_any(compact, ["gave", "given", "ate", "swallowed"]) else "moderate",
            info_sufficient=True,
            missing_facts=["medicine_name", "amount", "time_given"],
            scenario_type="unsafe_medicine",
            rationale="Human medicines and painkillers can be dangerous for dogs.",
        )

    if _contains_any(compact, ["kerosene", "engine oil", "turpentine", "acid", "chili", "turmeric"]) and _contains_any(
        compact, ["wound", "maggot", "skin", "apply", "put", "use"]
    ):
        return TriageResult(
            urgency_tier="moderate",
            info_sufficient=True,
            missing_facts=["what_was_applied", "skin_or_wound_status"],
            scenario_type="unsafe_home_remedy",
            rationale="Harsh or unproven home remedies can worsen wounds or poison the dog.",
        )

    if _contains_any(compact, ["well", "borewell", "pit", "shaft", "drain", "pipe", "sewer"]) and _contains_any(
        compact, ["fell", "fall", "fallen", "stuck", "trapped", "inside", "in a", "into"]
    ):
        return TriageResult(
            urgency_tier="life_threatening",
            info_sufficient=True,
            missing_facts=["is_dog_breathing", "approx_depth", "city_or_nearest_landmark"],
            scenario_type="fall_entrapment",
            needs_helpline_first=True,
            rationale="Entrapment in a confined vertical space needs rapid rescue help.",
        )

    if _contains_any(compact, ["bite", "bit", "scratch", "scratched", "saliva"]) and _contains_any(
        compact, ["my hand", "me", "person", "human", "skin", "blood", "broke the skin", "broken skin"]
    ):
        return TriageResult(
            urgency_tier="urgent",
            info_sufficient=True,
            missing_facts=["wound_washed", "rabies_vaccine_status", "dog_observable"],
            scenario_type="rabies_exposure",
            needs_helpline_first=False,
            rationale="A bite or scratch that breaks human skin needs rabies exposure assessment.",
        )

    if _contains_any(compact, ["heatstroke", "heat stroke", "overheat", "overheated"]):
        return TriageResult(
            urgency_tier="life_threatening" if _contains_any(compact, ["collapse", "confused", "vomit"]) else "urgent",
            info_sufficient=True,
            missing_facts=["temperature_exposure", "can_swallow"],
            scenario_type="heatstroke",
            rationale="Heat illness can deteriorate quickly.",
        )

    if _contains_any(compact, ["not breathing", "cannot breathe", "can't breathe", "choking", "blue gums"]):
        return TriageResult(
            urgency_tier="life_threatening",
            info_sufficient=True,
            missing_facts=["is_air_moving", "visible_object"],
            scenario_type="choking_airway",
            rationale="Airway or breathing distress can become fatal within minutes.",
        )

    if _contains_any(compact, ["unconscious", "unresponsive", "collapsed", "collapse", "repeated seizure"]):
        return TriageResult(
            urgency_tier="life_threatening",
            info_sufficient=True,
            missing_facts=["breathing_status", "duration"],
            scenario_type="seizure_collapse",
            rationale="Collapse or unresponsiveness is an emergency sign.",
        )

    if _contains_any(compact, ["heavy bleeding", "blood pouring", "non-stop bleeding", "spurting blood"]):
        return TriageResult(
            urgency_tier="life_threatening",
            info_sufficient=True,
            missing_facts=["bleeding_location"],
            scenario_type="severe_bleeding",
            rationale="Heavy bleeding needs immediate pressure and urgent help.",
        )

    if _contains_any(compact, ["hit by car", "road accident", "vehicle", "bike hit", "car hit", "hit by bike", "hit by a bike", "run over"]):
        tier = "life_threatening" if _contains_any(compact, ["cannot stand", "can't stand", "dragging", "collapsed"]) else "urgent"
        return TriageResult(
            urgency_tier=tier,
            info_sufficient=True,
            missing_facts=["can_stand", "breathing_status", "visible_bleeding"],
            scenario_type="road_trauma",
            needs_helpline_first=True,
            rationale="Road trauma can involve fractures, spinal injury, or internal injury.",
        )

    if _contains_any(compact, ["poison", "xylitol", "rat poison", "pesticide", "organophosphate", "chocolate"]):
        return TriageResult(
            urgency_tier="urgent",
            info_sufficient=True,
            missing_facts=["substance", "time_since_exposure", "symptoms"],
            scenario_type="poisoning",
            rationale="Suspected toxin exposure needs fast identification and vet guidance.",
        )

    if _contains_any(compact, ["maggot", "myiasis"]):
        return TriageResult(
            urgency_tier="urgent",
            info_sufficient=True,
            missing_facts=["wound_location", "dog_is_handleable"],
            scenario_type="maggot_wound",
            rationale="Maggot wounds need prompt wound care and rescue/vet treatment.",
        )

    if _contains_any(compact, ["tick", "ticks", "flea", "fleas"]):
        urgent = _contains_any(compact, ["weak", "pale", "bleeding", "fever", "not eating"])
        return TriageResult(
            urgency_tier="urgent" if urgent else "moderate",
            info_sufficient=True,
            missing_facts=["gum_color", "fever_or_weakness"],
            scenario_type="tick_infestation",
            rationale="Ticks can cause skin irritation and serious tick-borne illness when the dog is weak.",
        )

    if _contains_any(compact, ["mange", "hair loss", "itchy skin", "skin disease", "crusty skin"]):
        return TriageResult(
            urgency_tier="moderate",
            info_sufficient=True,
            missing_facts=["skin_broken_or_infected", "dog_is_weak"],
            scenario_type="skin_disease",
            rationale="Skin disease is described without immediate collapse or severe wound signs.",
        )

    if _contains_any(compact, ["fracture", "broken leg", "limping", "can't walk", "cannot walk"]):
        return TriageResult(
            urgency_tier="urgent",
            info_sufficient=True,
            missing_facts=["can_bear_weight", "pain_level"],
            scenario_type="fracture",
            rationale="Possible fracture needs immobilization and veterinary assessment.",
        )

    if _contains_any(compact, ["transport", "carry", "lift", "move him", "move her", "take to vet"]):
        return TriageResult(
            urgency_tier="moderate",
            info_sufficient=True,
            missing_facts=["possible_spinal_injury", "dog_size"],
            scenario_type="injured_transport",
            rationale="Transport advice should minimize pain and spinal movement.",
        )

    if _contains_any(compact, ["burn", "burned", "scald", "fire", "hot water", "chemical burn"]):
        return TriageResult(
            urgency_tier="urgent",
            info_sufficient=True,
            missing_facts=["burn_location", "burn_size", "chemical_or_heat"],
            scenario_type="burn_injury",
            rationale="Burns can worsen and may need urgent pain control and wound care.",
        )

    if _contains_any(compact, ["eye", "eyeball", "blind", "squinting"]):
        return TriageResult(
            urgency_tier="urgent",
            info_sufficient=True,
            missing_facts=["eye_open", "discharge_or_bleeding"],
            scenario_type="eye_injury",
            rationale="Eye injuries can worsen quickly without examination.",
        )

    if _contains_any(compact, ["puppy", "puppies"]) and _contains_any(compact, ["diarrhea", "diarrhoea", "vomit", "bloody"]):
        return TriageResult(
            urgency_tier="urgent",
            info_sufficient=True,
            missing_facts=["age", "blood_in_stool", "can_drink"],
            scenario_type="puppy_gi",
            rationale="Puppies can dehydrate and crash quickly.",
        )

    if _contains_any(compact, ["vomit", "vomiting", "diarrhea", "diarrhoea", "loose motion", "bloody stool"]):
        urgent = _contains_any(compact, ["repeated", "again and again", "blood", "bloody", "weak", "collapse", "puppy"])
        return TriageResult(
            urgency_tier="urgent" if urgent else "moderate",
            info_sufficient=True,
            missing_facts=["can_keep_water_down", "blood_present", "duration"],
            scenario_type="vomiting_diarrhea",
            rationale="Vomiting or diarrhea can become urgent if repeated, bloody, or causing weakness.",
        )

    if _contains_any(compact, ["aggressive", "biting", "growling", "lunging", "cornered"]):
        return TriageResult(
            urgency_tier="urgent",
            info_sufficient=True,
            missing_facts=["safe_distance", "injury_visible"],
            scenario_type="fearful_aggressive",
            needs_helpline_first=True,
            rationale="An aggressive or cornered dog needs distance and rescue support.",
        )

    if _contains_any(compact, ["lost dog", "found a dog", "missing dog", "stray followed", "near my building"]):
        return TriageResult(
            urgency_tier="low_risk",
            info_sufficient=True,
            missing_facts=["collar_or_tag", "safe_hold_location"],
            scenario_type="lost_dog",
            rationale="This is a welfare/logistics case unless injury or danger is present.",
        )

    if _contains_any(compact, ["feed", "food", "eat", "weak street dog", "hungry"]):
        return TriageResult(
            urgency_tier="low_risk" if not _contains_any(compact, ["collapse", "cannot stand", "very weak"]) else "moderate",
            info_sufficient=True,
            missing_facts=["can_swallow", "vomiting_or_diarrhea"],
            scenario_type="feeding_weak_dog",
            rationale="Feeding advice should be cautious, especially for weak or starved dogs.",
        )

    if _contains_any(compact, ["vaccine", "vaccination", "vaccines", "deworm", "deworming"]):
        return TriageResult(
            urgency_tier="low_risk",
            info_sufficient=True,
            missing_facts=["age", "previous_vaccines"],
            scenario_type="routine_care",
            rationale="Routine preventive care is not an emergency.",
        )

    if _contains_any(compact, ["healthy", "normal", "sleeping", "playing"]):
        return TriageResult(
            urgency_tier="low_risk",
            info_sufficient=True,
            scenario_type="healthy_or_low_risk",
            rationale="No urgent warning sign is described.",
        )

    return TriageResult(
        urgency_tier="moderate",
        info_sufficient=True,
        missing_facts=["breathing_status", "can_stand", "visible_injury"],
        scenario_type="unclear",
        rationale="Some detail is present, but the exact first-aid category is unclear.",
    )


async def classify_situation(
    user_message: str,
    analysis_context: str | None,
    last_assistant_message: str | None,
) -> TriageResult:
    """Classify a chat turn before generating a full response."""
    fallback = heuristic_classify_situation(user_message, analysis_context, last_assistant_message)
    settings = get_settings()
    if (
        not settings.groq_api_key
        or not fallback.info_sufficient
        or fallback.scenario_type in LOCAL_DECISION_SCENARIOS
    ):
        return fallback

    user_content = {
        "user_message": user_message,
        "analysis_context": analysis_context or "",
        "last_assistant_message": last_assistant_message or "",
        "heuristic_hint": fallback.model_dump(),
    }

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await groq_post_with_retry(
                client,
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json_body={
                    "model": settings.groq_triage_model,
                    "messages": [
                        {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
                        {"role": "user", "content": json.dumps(user_content, ensure_ascii=False)},
                    ],
                    "temperature": 0.0,
                    "max_tokens": 180,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            raw = json.loads(_extract_json_object(content))
            result = _normalize_result(raw, fallback)
            if fallback.scenario_type != "unclear" and result.scenario_type == "unclear":
                result.scenario_type = fallback.scenario_type
            if (
                fallback.scenario_type in {"poisoning", "fearful_aggressive"}
                and fallback.urgency_tier == "urgent"
                and result.urgency_tier == "life_threatening"
            ):
                result.urgency_tier = "urgent"
            return result
    except Exception as exc:
        logger.warning("Triage classification failed; using heuristic fallback: %s", exc)
        return fallback
