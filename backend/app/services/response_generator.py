"""Empathetic response and translation helpers for analysis results."""

import json
import logging
import re

import httpx

from app.config import get_settings
from app.services.groq_retry import groq_post_with_retry
from app.services.triage import heuristic_classify_situation

logger = logging.getLogger(__name__)

DISCLAIMERS = {
    "en": (
        "This is AI-based guidance, not a veterinary diagnosis. "
        "When in doubt, please contact a veterinary professional immediately."
    ),
    "hi": "यह AI-आधारित मार्गदर्शन है, पशु-चिकित्सकीय निदान नहीं। संदेह होने पर तुरंत पशु-चिकित्सक से संपर्क करें।",
    "mr": "हे AI-आधारित मार्गदर्शन आहे, पशुवैद्यकीय निदान नाही. शंका असल्यास त्वरित पशुवैद्यकाशी संपर्क करा.",
}

LANGUAGE_INSTRUCTIONS = {
    "en": "Respond in English.",
    "hi": (
        "CRITICAL LANGUAGE RULE: You MUST respond ENTIRELY in Hindi using Devanagari script. "
        "Do NOT use Roman transliteration. Keep medicine brand names in English."
    ),
    "mr": (
        "CRITICAL LANGUAGE RULE: You MUST respond ENTIRELY in Marathi using Devanagari script. "
        "Do NOT use Roman transliteration. Keep medicine brand names in English."
    ),
}

LANGUAGE_REMINDERS = {
    "en": "",
    "hi": "\n\nकृपया पूरा उत्तर हिन्दी में दें।",
    "mr": "\n\nकृपया संपूर्ण उत्तर मराठीत द्या।",
}

TRANSLATION_INSTRUCTIONS = {
    "hi": "Hindi using Devanagari script",
    "mr": "Marathi using Devanagari script",
}

SYSTEM_PROMPT = """You are IndieAid, a compassionate AI assistant that helps people care for dogs with grounded first-aid guidance.

You are NOT a veterinarian. Your role is to help the rescuer act safely and clearly based on what is visible, while admitting uncertainty when the image is not enough.

{language_instruction}

Safety rules:
- Be decisive when the picture strongly suggests a problem.
- If the picture is ambiguous, explain the most likely possibilities, what the rescuer should check next, and which first-aid steps are safe across those possibilities.
- Do not give prescription medication plans, injections, antibiotics, steroids, painkillers, dewormers, anti-diarrhoeals, or human medicines.
- Do not invent medicine doses.
- You may recommend only low-risk first aid such as moving to shade, offering water if safe, direct pressure for bleeding, saline rinsing, diluted povidone-iodine on superficial wounds, keeping the dog warm, limiting movement, using a clean cloth or gauze, and rapid transport for urgent cases.
- Explicitly warn against unsafe remedies like kerosene, turpentine, engine oil, acid, chili, or random human over-the-counter drugs.

Urgency rules:
- Use "danger" when the image suggests a high-risk situation such as severe bleeding, inability to stand, obvious fracture, collapse, heavy breathing distress, severe eye injury, maggot wounds, serious road trauma, or another situation that needs rapid professional care.
- Use "caution" when the dog may still be approachable but there is pain, fear, visible illness, or uncertainty that warrants care.
- Use "safe" only when the dog looks stable and approachable with no obvious emergency signs.

Respond with valid JSON only:
{{
  "condition": {{
    "breed_guess": "translated or transliterated breed text",
    "estimated_age": "translated age label",
    "physical_condition": "translated physical-condition summary",
    "visible_injuries": ["translated visible injuries"],
    "health_concerns": ["translated health concerns"],
    "body_language": "translated body-language summary"
  }},
  "safety_level": "safe" | "caution" | "danger",
  "safety_reason": "brief explanation",
  "empathetic_summary": "2-3 warm sentences for the rescuer",
  "first_aid_steps": [
    {{"step_number": 1, "instruction": "clear actionable step"}},
    {{"step_number": 2, "instruction": "clear actionable step"}}
  ],
  "triage_questions": ["only when more info is needed before first aid"],
  "urgency_tier": "life_threatening" | "urgent" | "moderate" | "low_risk" | "unclear",
  "info_sufficient": true | false,
  "needs_helpline_first": true | false,
  "when_to_call_professional": "one sentence about when professional help is needed",
  "approach_tips": "one or two sentences on how to approach the dog safely"
}}

Rules:
- Safety level must match the dog's visible behavior and injuries
- Translate the provided condition facts into the target language without changing the underlying meaning
- Keep first aid steps simple for a non-expert
- Use 3 to 5 first aid steps
- For life-threatening scene context, use only 1 to 3 immediate steps and skip nonessential monitoring advice
- If the image/context is too vague to choose safe first aid, set info_sufficient=false and provide 1-2 triage_questions instead of filling first_aid_steps
- Keep steps grounded in what is visible
- Say clearly when veterinary or rescue help is needed
- Do not wrap the JSON in markdown
"""

TRANSLATION_SYSTEM_PROMPT = """You translate IndieAid analysis JSON for the UI.

Return ONLY valid JSON with the exact same keys and array structure as the source object.

Rules:
- Translate every user-facing string into {language_name}
- Every user-facing sentence must be fully written in {language_name}; leaving English text behind is invalid
- Preserve facts, meaning, tone, safety_level, step numbers, medicine names, and phone numbers
- Do not add new advice or remove any advice
- If the breed has no common translation, transliterate it into Devanagari or use a natural local phrase
- Do not wrap the JSON in markdown
"""

TRANSLATION_REPAIR_SYSTEM_PROMPT = """You repair an IndieAid translation JSON that still contains English text.

Return ONLY valid JSON with the exact same keys and array structure as the source object.

Rules:
- Rewrite EVERY user-facing string into {language_name}
- Do not leave English words or English sentences in fields like estimated_age, physical_condition, body_language, safety_reason, empathetic_summary, first_aid_steps, when_to_call_professional, or approach_tips
- Preserve meaning, tone, safety_level, step numbers, medicine names, and phone numbers
- Do not add new advice or remove any advice
- Do not wrap the JSON in markdown
"""

DEFAULT_CONDITION = {
    "breed_guess": "Unable to determine (analysis unavailable)",
    "estimated_age": "Unknown",
    "physical_condition": "Could not analyze - please consult a veterinarian.",
    "visible_injuries": [],
    "health_concerns": [],
    "body_language": "Could not analyze",
}

DEFAULT_CONDITION_TRANSLATIONS = {
    "hi": {
        "Unable to determine (analysis unavailable)": "निर्धारित नहीं किया जा सका (विश्लेषण उपलब्ध नहीं है)",
        "Unable to determine (no dog visible)": "निर्धारित नहीं किया जा सका (कुत्ता दिखाई नहीं दे रहा है)",
        "Unknown": "अज्ञात",
        "Could not analyze - please consult a veterinarian.": "विश्लेषण नहीं हो सका। कृपया पशु-चिकित्सक से सलाह लें।",
        "Could not analyze": "विश्लेषण नहीं हो सका",
        "No dog was visible in the image.": "छवि में कोई कुत्ता दिखाई नहीं दे रहा था।",
        "No dog visible": "कोई कुत्ता दिखाई नहीं दे रहा",
        "adult": "वयस्क",
        "young adult": "युवा वयस्क",
        "puppy": "पिल्ला",
        "senior": "वरिष्ठ",
        "Indian pariah / mixed breed": "इंडियन पैरियाह / मिश्रित नस्ल",
    },
    "mr": {
        "Unable to determine (analysis unavailable)": "ठरवता आले नाही (विश्लेषण उपलब्ध नाही)",
        "Unable to determine (no dog visible)": "ठरवता आले नाही (कुत्रा दिसत नाही)",
        "Unknown": "अज्ञात",
        "Could not analyze - please consult a veterinarian.": "विश्लेषण करता आले नाही. कृपया पशुवैद्यकाशी संपर्क करा.",
        "Could not analyze": "विश्लेषण करता आले नाही",
        "No dog was visible in the image.": "प्रतिमेत कोणताही कुत्रा दिसत नव्हता.",
        "No dog visible": "कुत्रा दिसत नाही",
        "adult": "प्रौढ",
        "young adult": "तरुण प्रौढ",
        "puppy": "पिल्लू",
        "senior": "वृद्ध",
        "Indian pariah / mixed breed": "इंडियन पॅराया / मिश्र जात",
    },
}

FALLBACK_EMOTION_TEXT = {
    "en": {
        "happy": "happy",
        "sad": "sad",
        "angry": "angry",
        "relaxed": "relaxed",
        "fearful": "fearful",
        "unknown": "uncertain",
    },
    "hi": {
        "happy": "खुश",
        "sad": "उदास",
        "angry": "गुस्से में",
        "relaxed": "शांत",
        "fearful": "डरा हुआ",
        "unknown": "अनिश्चित",
    },
    "mr": {
        "happy": "आनंदी",
        "sad": "दुःखी",
        "angry": "रागावलेला",
        "relaxed": "शांत",
        "fearful": "घाबरलेला",
        "unknown": "अनिश्चित",
    },
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


def _has_devanagari(text: str) -> bool:
    return any("\u0900" <= char <= "\u097F" for char in text)


def _iter_strings(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)


def _translation_coverage_ok(raw: dict | None, language: str) -> bool:
    if language == "en":
        return True
    if not isinstance(raw, dict):
        return False

    for text in _iter_strings(raw):
        cleaned = text.strip()
        if not cleaned:
            continue
        if re.search(r"[A-Za-z]", cleaned) and not _has_devanagari(cleaned):
            return False
    return True


def _clean_text(value: object, fallback: str) -> str:
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            return cleaned
    return fallback


def _clean_string_list(value: object, limit: int = 3) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        if isinstance(item, str):
            cleaned = item.strip()
            if cleaned:
                items.append(cleaned)
        if len(items) >= limit:
            break
    return items


def _normalize_first_aid_steps(
    raw_steps: object,
    fallback_steps: list[dict],
    min_steps: int = 3,
    max_steps: int = 5,
) -> list[dict]:
    if not isinstance(raw_steps, list) or not raw_steps:
        return fallback_steps[:max_steps]

    normalized: list[dict] = []
    for index, raw_step in enumerate(raw_steps[:max_steps]):
        fallback_step = fallback_steps[index] if index < len(fallback_steps) else {"instruction": ""}
        instruction = fallback_step.get("instruction", "")
        if isinstance(raw_step, dict):
            instruction = _clean_text(raw_step.get("instruction"), instruction)
        elif isinstance(raw_step, str):
            instruction = _clean_text(raw_step, instruction)
        if instruction:
            normalized.append({"step_number": len(normalized) + 1, "instruction": instruction})

    if len(normalized) < min_steps:
        for fallback_step in fallback_steps[len(normalized) : max_steps]:
            normalized.append(
                {
                    "step_number": len(normalized) + 1,
                    "instruction": fallback_step["instruction"],
                }
            )
            if len(normalized) >= min_steps:
                break
    return normalized[:max_steps]


def _localize_condition_text(text: str, language: str) -> str:
    if language == "en":
        return text
    return DEFAULT_CONDITION_TRANSLATIONS.get(language, {}).get(text, text)


def _fallback_condition(condition_result: dict, language: str) -> dict:
    base = condition_result or DEFAULT_CONDITION
    return {
        "breed_guess": _localize_condition_text(
            str(base.get("breed_guess") or DEFAULT_CONDITION["breed_guess"]),
            language,
        ),
        "estimated_age": _localize_condition_text(
            str(base.get("estimated_age") or DEFAULT_CONDITION["estimated_age"]),
            language,
        ),
        "physical_condition": _localize_condition_text(
            str(base.get("physical_condition") or DEFAULT_CONDITION["physical_condition"]),
            language,
        ),
        "visible_injuries": [
            _localize_condition_text(str(item), language)
            for item in (base.get("visible_injuries") or [])
            if str(item).strip()
        ],
        "health_concerns": [
            _localize_condition_text(str(item), language)
            for item in (base.get("health_concerns") or [])
            if str(item).strip()
        ],
        "body_language": _localize_condition_text(
            str(base.get("body_language") or DEFAULT_CONDITION["body_language"]),
            language,
        ),
    }


def _lower_values(items: object) -> str:
    if not isinstance(items, list):
        return ""
    return " ".join(str(item).lower() for item in items if str(item).strip())


def _analysis_family(emotion_label: str, condition_result: dict, user_context: str | None = None) -> str:
    condition_text = " ".join(
        [
            str(condition_result.get("breed_guess", "")),
            str(condition_result.get("physical_condition", "")),
            _lower_values(condition_result.get("visible_injuries")),
            _lower_values(condition_result.get("health_concerns")),
            str(condition_result.get("body_language", "")),
            str(user_context or ""),
        ]
    ).lower()

    if "analysis unavailable" in condition_text or "could not analyze" in condition_text:
        return "unavailable"
    if "no dog visible" in condition_text or "no dog was visible" in condition_text:
        return "no_dog_visible"
    if any(term in condition_text for term in ["not breathing", "collapse", "collapsed", "severe bleeding", "spurting", "hit by car", "road accident", "poison", "heatstroke", "trapped", "fracture"]):
        return "immediate_emergency"
    if any(term in condition_text for term in ["bleeding", "wound", "maggot", "cannot stand", "limping badly", "swollen eye", "eye injury"]):
        return "urgent_stable"
    if any(term in condition_text for term in ["skin", "tick", "mange", "rash", "thin", "underweight", "limp", "diarrhea", "vomit"]):
        return "mild_concern"
    if emotion_label in {"sad", "fearful"}:
        return "sad_quiet"
    if any(term in condition_text for term in ["stray", "community", "street"]):
        return "healthy_stray"
    return "healthy_pet"


def _fallback_family_response(family: str, language: str) -> dict | None:
    if language == "hi":
        data = {
            "healthy_pet": (
                "safe",
                "\u092b\u094b\u091f\u094b \u092e\u0947\u0902 \u0924\u0941\u0930\u0902\u0924 \u0916\u0924\u0930\u0947 \u0915\u093e \u0938\u093e\u092b \u0938\u0902\u0915\u0947\u0924 \u0928\u0939\u0940\u0902 \u0926\u093f\u0916 \u0930\u0939\u093e\u0964",
                "\u092b\u094b\u091f\u094b \u092e\u0947\u0902 \u092f\u0939 \u0915\u0941\u0924\u094d\u0924\u093e \u0915\u093e\u092b\u0940 \u0938\u094d\u0925\u093f\u0930 \u0926\u093f\u0916 \u0930\u0939\u093e \u0939\u0948\u0964 \u0925\u094b\u0921\u093c\u093e \u092a\u093e\u0928\u0940, \u0936\u093e\u0902\u0924 \u0926\u0942\u0930\u0940, \u0914\u0930 \u0906\u0917\u0947 \u0915\u094b\u0908 \u092c\u0926\u0932\u093e\u0935 \u0926\u093f\u0916\u0947 \u0924\u094b \u0927\u094d\u092f\u093e\u0928 \u0930\u0916\u0928\u093e \u0915\u093e\u092b\u0940 \u0939\u0948\u0964",
            ),
            "unavailable": (
                "caution",
                "\u0935\u093f\u091c\u0928 \u0935\u093f\u0936\u094d\u0932\u0947\u0937\u0923 \u0909\u092a\u0932\u092c\u094d\u0927 \u0928\u0939\u0940\u0902 \u0939\u0948\u0964",
                "\u092e\u0948\u0902 \u0907\u0938 \u092b\u094b\u091f\u094b \u0915\u094b \u0905\u092d\u0940 \u092a\u0922\u093c \u0928\u0939\u0940\u0902 \u0938\u0915\u093e\u0964 \u0905\u0917\u0930 \u0938\u093e\u0902\u0938, \u0916\u0942\u0928, \u0917\u093f\u0930\u0928\u093e, \u091c\u0939\u0930 \u092f\u093e \u0938\u0921\u093c\u0915 \u091a\u094b\u091f \u0915\u093e \u0936\u0915 \u0939\u0948, \u0924\u094b \u091a\u0948\u091f \u092e\u0947\u0902 \u0924\u0941\u0930\u0902\u0924 \u0935\u093f\u0935\u0930\u0923 \u0926\u0947\u0902\u0964",
            ),
        }
        level, reason, summary = data.get(family, data["healthy_pet"])
    elif language == "mr":
        data = {
            "healthy_pet": (
                "safe",
                "\u092b\u094b\u091f\u094b\u0924 \u0924\u093e\u0924\u0921\u0940\u091a\u094d\u092f\u093e \u0927\u094b\u0915\u094d\u092f\u093e\u091a\u093e \u0938\u094d\u092a\u0937\u094d\u091f \u0938\u0902\u0915\u0947\u0924 \u0926\u093f\u0938\u0924 \u0928\u093e\u0939\u0940\u0964",
                "\u092b\u094b\u091f\u094b\u0924 \u0939\u093e \u0915\u0941\u0924\u094d\u0930\u093e \u0924\u0941\u0932\u0928\u0947\u0928\u0947 \u0938\u094d\u0925\u093f\u0930 \u0926\u093f\u0938\u0924\u094b\u0964 \u0938\u094d\u0935\u091a\u094d\u091b \u092a\u093e\u0923\u0940, \u0936\u093e\u0902\u0924 \u0905\u0902\u0924\u0930, \u0906\u0923\u093f \u0915\u093e\u0939\u0940 \u092c\u0926\u0932 \u0926\u093f\u0938\u0932\u093e \u0924\u0930 \u0928\u093f\u0930\u0940\u0915\u094d\u0937\u0923 \u092a\u0941\u0930\u0947\u0938\u0947 \u0906\u0939\u0947\u0964",
            ),
            "unavailable": (
                "caution",
                "\u0935\u093f\u091c\u0928 \u0935\u093f\u0936\u094d\u0932\u0947\u0937\u0923 \u0909\u092a\u0932\u092c\u094d\u0927 \u0928\u093e\u0939\u0940\u0964",
                "\u092e\u0940 \u0939\u093e \u092b\u094b\u091f\u094b \u0938\u0927\u094d\u092f\u093e \u0935\u093e\u091a\u0942 \u0936\u0915\u0932\u094b \u0928\u093e\u0939\u0940\u0964 \u0936\u094d\u0935\u093e\u0938, \u0930\u0915\u094d\u0924, \u0915\u094b\u0938\u0933\u0923\u0947, \u0935\u093f\u0937 \u0915\u093f\u0902\u0935\u093e \u0930\u0938\u094d\u0924\u094d\u092f\u093e\u0935\u0930\u0940\u0932 \u0905\u092a\u0918\u093e\u0924\u093e\u091a\u093e \u0936\u0902\u0915\u093e \u0905\u0938\u0947\u0932, \u0924\u0930 \u091a\u0945\u091f\u092e\u0927\u094d\u092f\u0947 \u0924\u092a\u0936\u0940\u0932 \u0926\u094d\u092f\u093e\u0964",
            ),
        }
        level, reason, summary = data.get(family, data["healthy_pet"])
    else:
        data = {
            "healthy_pet": ("safe", "No immediate danger is clear from the photo.", "The dog looks fairly settled in this photo. Offer clean water, keep things calm, and watch for any new changes rather than treating this like an urgent case."),
            "healthy_stray": ("safe", "No immediate danger is clear, but keep a respectful distance.", "This community dog looks fairly stable from the photo. Give space, offer water or food only if safe, and avoid crowding or grabbing."),
            "sad_quiet": ("caution", "The dog looks quiet or uncertain, but no clear emergency is visible.", "The photo suggests a quieter or unsure dog rather than a definite emergency. Keep the area calm, check breathing and ability to stand, and watch for worsening signs."),
            "mild_concern": ("caution", "There may be a mild concern worth monitoring.", "I can see a possible care concern, but this does not read like an immediate emergency from the available information. Keep the dog comfortable and watch closely for worsening signs."),
            "urgent_stable": ("caution", "A visible concern may need prompt veterinary or rescue help.", "This looks like it may need prompt care. Keep the dog calm, avoid handling painful areas, and arrange veterinary or rescue help if the concern is confirmed."),
            "immediate_emergency": ("danger", "The photo or context suggests a possible emergency.", "This may be urgent. Focus on safety first, limit movement, and contact a vet, rescue group, or emergency help now."),
            "no_dog_visible": ("caution", "No dog is visible enough to assess.", "I could not see a dog clearly in this photo. Try another image with the dog well lit and fully visible."),
            "unavailable": ("caution", "Vision analysis is unavailable right now.", "I could not analyze this photo right now. If the dog may be in danger, use the chat and describe breathing, bleeding, movement, and what happened."),
        }
        level, reason, summary = data.get(family, data["healthy_pet"])

    steps_by_family = {
        "healthy_pet": [],
        "healthy_stray": [{"step_number": 1, "instruction": "Offer water or food only from a calm, safe distance."}],
        "sad_quiet": [{"step_number": 1, "instruction": "Check from a distance whether breathing looks normal and whether the dog can stand."}],
        "mild_concern": [{"step_number": 1, "instruction": "Monitor appetite, water intake, energy, stool, and any visible skin or eye changes."}],
        "urgent_stable": [{"step_number": 1, "instruction": "Avoid pressing or pulling painful areas; keep the dog quiet while arranging help."}],
        "immediate_emergency": [{"step_number": 1, "instruction": "Keep yourself safe, limit the dog's movement, and contact urgent veterinary or rescue help now."}],
        "no_dog_visible": [],
        "unavailable": [],
    }
    return {
        "safety_level": level,
        "safety_reason": reason,
        "empathetic_summary": summary,
        "first_aid_steps": steps_by_family.get(family, []),
        "triage_questions": [],
        "urgency_tier": "urgent" if family in {"urgent_stable", "immediate_emergency"} else "low_risk",
        "info_sufficient": family not in {"no_dog_visible", "unavailable"},
        "needs_helpline_first": family == "immediate_emergency",
        "when_to_call_professional": (
            "Get professional help now if breathing is abnormal, bleeding is heavy, the dog cannot stand, pain is severe, or symptoms worsen."
            if language == "en" and family not in {"healthy_pet", "healthy_stray", "no_dog_visible", "unavailable"}
            else ""
        ),
        "approach_tips": (
            "Approach slowly from the side, avoid direct staring, and stop if the dog seems fearful or defensive."
            if language == "en" and family not in {"no_dog_visible", "unavailable"}
            else ""
        ),
    }


def _fallback_response(emotion_result: dict, condition_result: dict, language: str) -> dict:
    emotion_label = str(emotion_result.get("label", "unknown")).strip().lower()
    family = _analysis_family(emotion_label, condition_result)
    family_payload = _fallback_family_response(family, language)
    if family_payload is not None:
        return family_payload

    emotion_text = FALLBACK_EMOTION_TEXT.get(language, FALLBACK_EMOTION_TEXT["en"]).get(
        emotion_label,
        FALLBACK_EMOTION_TEXT.get(language, FALLBACK_EMOTION_TEXT["en"])["unknown"],
    )
    has_injuries = bool(condition_result.get("visible_injuries"))
    has_concerns = bool(condition_result.get("health_concerns"))

    if language == "hi":
        safety_reason = (
            f"कुत्ता {emotion_text} दिख रहा है, इसलिए धीरे और सावधानी से पास जाएं।"
            if emotion_label in {"angry", "fearful"}
            else f"कुत्ता {emotion_text} दिख रहा है और फिलहाल अपेक्षाकृत सुरक्षित लगता है।"
        )
        summary = (
            f"यह कुत्ता अभी {emotion_text} दिख रहा है। शांत रहें, धीरे-धीरे पास जाएं, "
            "और जरूरत हो तो तुरंत पेशेवर मदद लें।"
        )
        steps = [
            {"step_number": 1, "instruction": "धीरे-धीरे पास जाएं और अचानक हरकत न करें।"},
            {"step_number": 2, "instruction": "थोड़ी दूरी से साफ पानी दें।"},
            {"step_number": 3, "instruction": "धीमी और शांत आवाज़ में बात करें ताकि कुत्ता घबराए नहीं।"},
        ]
        if has_injuries or has_concerns:
            steps.append(
                {
                    "step_number": 4,
                    "instruction": "दिखाई देने वाले घाव को छेड़ें नहीं। जरूरत हो तो पतला Betadine और साफ कपड़ा तैयार रखें।",
                }
            )
            steps.append(
                {
                    "step_number": 5,
                    "instruction": "यदि खून, सूजन, गंभीर खुजली, या चलने में दिक्कत दिखे तो पशु-चिकित्सक या स्थानीय NGO से तुरंत मदद लें।",
                }
            )
        return {
            "safety_level": "caution" if emotion_label in {"angry", "fearful"} else "safe",
            "safety_reason": safety_reason,
            "empathetic_summary": summary,
            "first_aid_steps": steps,
            "when_to_call_professional": "अगर खून बह रहा हो, सांस लेने में दिक्कत हो, हड्डी टूटी लगे, या कुत्ता उठ न पा रहा हो तो तुरंत पशु-चिकित्सक से संपर्क करें।",
            "approach_tips": "अपने शरीर को थोड़ा तिरछा रखें, सीधे आंखों में न देखें, और कुत्ते को आपके पास आने का समय दें।",
        }

    if language == "mr":
        safety_reason = (
            f"कुत्रा {emotion_text} दिसत आहे, त्यामुळे हळू आणि काळजीपूर्वक जवळ जा."
            if emotion_label in {"angry", "fearful"}
            else f"कुत्रा {emotion_text} दिसत आहे आणि सध्या तुलनेने सुरक्षित वाटतो."
        )
        summary = (
            f"हा कुत्रा सध्या {emotion_text} दिसत आहे. शांत रहा, हळूवार जवळ जा, "
            "आणि गरज वाटल्यास त्वरित तज्ज्ञ मदत घ्या."
        )
        steps = [
            {"step_number": 1, "instruction": "हळूवार जवळ जा आणि अचानक हालचाल करू नका."},
            {"step_number": 2, "instruction": "थोड्या अंतरावरून स्वच्छ पाणी द्या."},
            {"step_number": 3, "instruction": "कुत्रा घाबरू नये म्हणून शांत आवाजात बोला."},
        ]
        if has_injuries or has_concerns:
            steps.append(
                {
                    "step_number": 4,
                    "instruction": "दिसणाऱ्या जखमेवर हात लावू नका. गरज भासल्यास पातळ Betadine आणि स्वच्छ कापड तयार ठेवा.",
                }
            )
            steps.append(
                {
                    "step_number": 5,
                    "instruction": "रक्तस्त्राव, सूज, तीव्र खाज, किंवा चालण्यात अडचण दिसल्यास पशुवैद्य किंवा स्थानिक NGO शी त्वरित संपर्क करा.",
                }
            )
        return {
            "safety_level": "caution" if emotion_label in {"angry", "fearful"} else "safe",
            "safety_reason": safety_reason,
            "empathetic_summary": summary,
            "first_aid_steps": steps,
            "when_to_call_professional": "रक्तस्त्राव, श्वास घेण्यास त्रास, हाड मोडल्याची शंका, किंवा कुत्रा उभा राहू शकत नसेल तर त्वरित पशुवैद्यकाशी संपर्क करा.",
            "approach_tips": "शरीर थोडे बाजूला वळवून उभे रहा, थेट डोळ्यात डोळे लावू नका, आणि कुत्र्याला तुमच्याजवळ येण्यासाठी वेळ द्या.",
        }

    safety_reason = (
        f"The dog appears {emotion_text}. Approach slowly and carefully."
        if emotion_label in {"angry", "fearful"}
        else f"The dog appears {emotion_text}. It seems approachable."
    )
    steps = [
        {"step_number": 1, "instruction": "Approach the dog slowly and calmly. Avoid sudden movements."},
        {"step_number": 2, "instruction": "Offer clean water in a shallow bowl from a safe distance."},
        {"step_number": 3, "instruction": "Speak softly to reassure the dog."},
    ]
    if has_injuries or has_concerns:
        steps.append(
            {
                "step_number": 4,
                "instruction": "Do not touch visible wounds. If needed, prepare diluted Betadine and a clean cloth for basic first aid.",
            }
        )
        steps.append(
            {
                "step_number": 5,
                "instruction": "Seek veterinary or NGO help if you notice bleeding, swelling, severe skin disease, or trouble walking.",
            }
        )
    return {
        "safety_level": "caution" if emotion_label in {"angry", "fearful"} else "safe",
        "safety_reason": safety_reason,
        "empathetic_summary": (
            f"You've found a dog that seems {emotion_text}. Stay calm, approach gently, "
            "and get professional help if the dog looks injured or unwell."
        ),
        "first_aid_steps": steps,
        "when_to_call_professional": "Contact a veterinarian immediately if you see bleeding, breathing trouble, fractures, or the dog cannot stand.",
        "approach_tips": "Turn your body slightly sideways, avoid direct eye contact, and give the dog time to approach you.",
    }


async def _call_groq_json(system_prompt: str, user_content: str, max_tokens: int = 1000) -> dict | None:
    settings = get_settings()
    if not settings.groq_api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=35.0) as client:
            response = await groq_post_with_retry(
                client,
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json_body={
                    "model": settings.groq_text_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    "temperature": 0.2,
                    "max_tokens": max_tokens,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(_extract_json_object(content))
    except Exception as exc:
        logger.error(f"Groq JSON generation failed: {exc}")
        return None


def _normalize_response_payload(raw: dict | None, emotion_result: dict, condition_result: dict, language: str) -> dict:
    fallback = _fallback_response(emotion_result, condition_result, language)
    if not isinstance(raw, dict):
        return fallback

    urgency_tier = str(raw.get("urgency_tier", "")).strip().lower()
    if urgency_tier not in {"life_threatening", "urgent", "moderate", "low_risk", "unclear"}:
        urgency_tier = "urgent" if str(raw.get("safety_level", "")).strip().lower() == "danger" else "unclear"
    info_sufficient = bool(raw.get("info_sufficient", True))
    needs_helpline_first = bool(raw.get("needs_helpline_first", False))
    triage_questions = _clean_string_list(raw.get("triage_questions"), limit=2)

    safety_level = str(raw.get("safety_level", fallback["safety_level"])).strip().lower()
    if safety_level not in {"safe", "caution", "danger"}:
        safety_level = fallback["safety_level"]

    source_payload = {
        "emotion": emotion_result,
        "condition": condition_result,
        "safety_level": fallback["safety_level"],
        "safety_reason": fallback["safety_reason"],
        "empathetic_summary": fallback["empathetic_summary"],
        "first_aid_steps": fallback["first_aid_steps"],
        "when_to_call_professional": fallback["when_to_call_professional"],
        "approach_tips": fallback["approach_tips"],
    }
    normalized_condition = _normalize_translated_payload(
        {"condition": raw.get("condition", {})} if isinstance(raw.get("condition"), dict) else None,
        source_payload,
        language,
    )["condition"]

    if not info_sufficient and triage_questions:
        return {
            "condition": normalized_condition,
            "safety_level": "caution",
            "safety_reason": _clean_text(raw.get("safety_reason"), "A few details are needed before choosing first aid."),
            "empathetic_summary": _clean_text(raw.get("empathetic_summary"), fallback["empathetic_summary"]),
            "first_aid_steps": [],
            "triage_questions": triage_questions,
            "urgency_tier": urgency_tier,
            "info_sufficient": False,
            "needs_helpline_first": needs_helpline_first,
            "when_to_call_professional": "",
            "approach_tips": _clean_text(raw.get("approach_tips"), fallback["approach_tips"]),
        }

    min_steps = 1 if urgency_tier == "life_threatening" else 3
    max_steps = 3 if urgency_tier == "life_threatening" else 5
    when_to_call = _clean_text(
        raw.get("when_to_call_professional"),
        fallback["when_to_call_professional"],
    )
    if urgency_tier == "life_threatening" and needs_helpline_first:
        when_to_call = _clean_text(raw.get("when_to_call_professional"), "")

    return {
        "condition": normalized_condition,
        "safety_level": safety_level,
        "safety_reason": _clean_text(raw.get("safety_reason"), fallback["safety_reason"]),
        "empathetic_summary": _clean_text(raw.get("empathetic_summary"), fallback["empathetic_summary"]),
        "first_aid_steps": _normalize_first_aid_steps(
            raw.get("first_aid_steps"),
            fallback["first_aid_steps"],
            min_steps=min_steps,
            max_steps=max_steps,
        ),
        "triage_questions": triage_questions,
        "urgency_tier": urgency_tier,
        "info_sufficient": info_sufficient,
        "needs_helpline_first": needs_helpline_first,
        "when_to_call_professional": when_to_call,
        "approach_tips": _clean_text(raw.get("approach_tips"), fallback["approach_tips"]),
    }


def _normalize_translated_payload(raw: dict | None, source_payload: dict, language: str) -> dict:
    translated_fallback = _fallback_response(source_payload["emotion"], source_payload["condition"], language)
    fallback_condition = _fallback_condition(source_payload["condition"], language)

    raw_condition = raw.get("condition") if isinstance(raw, dict) and isinstance(raw.get("condition"), dict) else {}
    translated_steps = raw.get("first_aid_steps") if isinstance(raw, dict) else None

    return {
        "condition": {
            "breed_guess": _localize_condition_text(
                _clean_text(raw_condition.get("breed_guess"), fallback_condition["breed_guess"]),
                language,
            ),
            "estimated_age": _localize_condition_text(
                _clean_text(raw_condition.get("estimated_age"), fallback_condition["estimated_age"]),
                language,
            ),
            "physical_condition": _localize_condition_text(
                _clean_text(raw_condition.get("physical_condition"), fallback_condition["physical_condition"]),
                language,
            ),
            "visible_injuries": [
                _localize_condition_text(
                    _clean_text(item, fallback_condition["visible_injuries"][index] if index < len(fallback_condition["visible_injuries"]) else ""),
                    language,
                )
                for index, item in enumerate(raw_condition.get("visible_injuries", []))
                if _clean_text(item, "").strip()
            ] or fallback_condition["visible_injuries"],
            "health_concerns": [
                _localize_condition_text(
                    _clean_text(item, fallback_condition["health_concerns"][index] if index < len(fallback_condition["health_concerns"]) else ""),
                    language,
                )
                for index, item in enumerate(raw_condition.get("health_concerns", []))
                if _clean_text(item, "").strip()
            ] or fallback_condition["health_concerns"],
            "body_language": _localize_condition_text(
                _clean_text(raw_condition.get("body_language"), fallback_condition["body_language"]),
                language,
            ),
        },
        "safety_level": source_payload["safety_level"],
        "safety_reason": _clean_text(
            raw.get("safety_reason") if isinstance(raw, dict) else None,
            translated_fallback["safety_reason"],
        ),
        "empathetic_summary": _clean_text(
            raw.get("empathetic_summary") if isinstance(raw, dict) else None,
            translated_fallback["empathetic_summary"],
        ),
        "first_aid_steps": _normalize_first_aid_steps(
            translated_steps,
            translated_fallback["first_aid_steps"],
        ),
        "triage_questions": _clean_string_list(
            raw.get("triage_questions") if isinstance(raw, dict) else None,
            limit=2,
        ),
        "when_to_call_professional": _clean_text(
            raw.get("when_to_call_professional") if isinstance(raw, dict) else None,
            translated_fallback["when_to_call_professional"],
        ),
        "approach_tips": _clean_text(
            raw.get("approach_tips") if isinstance(raw, dict) else None,
            translated_fallback["approach_tips"],
        ),
        "disclaimer": DISCLAIMERS.get(language, DISCLAIMERS["en"]),
    }


async def generate_empathetic_response(
    emotion_result: dict,
    condition_result: dict,
    language: str = "en",
    user_context: str | None = None,
) -> dict:
    """Generate a structured response for a single language."""
    settings = get_settings()
    if not settings.groq_api_key:
        logger.warning("Groq API key not set; returning fallback response.")
        return _fallback_response(emotion_result, condition_result, language)

    system_prompt = SYSTEM_PROMPT.format(
        language_instruction=LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["en"])
    )
    analysis_summary = f"""Dog Analysis Results:
- Emotional State: {emotion_result.get('label', 'unknown')} (confidence: {emotion_result.get('confidence', 0)})
- Emotion Description: {emotion_result.get('description', '')}
- Breed Guess: {condition_result.get('breed_guess', 'unknown')}
- Estimated Age: {condition_result.get('estimated_age', 'unknown')}
- Physical Condition: {condition_result.get('physical_condition', 'unknown')}
- Visible Injuries: {', '.join(condition_result.get('visible_injuries', [])) or 'None observed'}
- Health Concerns: {', '.join(condition_result.get('health_concerns', [])) or 'None observed'}
- Body Language: {condition_result.get('body_language', 'unknown')}"""
    context_triage = None
    if user_context and user_context.strip():
        context_triage = heuristic_classify_situation(user_context)
        analysis_summary += (
            f"\n- User-Provided Scene Context: {user_context.strip()[:1000]}"
            f"\n- Context Triage Hint: {context_triage.model_dump()}"
        )
    analysis_summary += LANGUAGE_REMINDERS.get(language, "")

    raw = await _call_groq_json(system_prompt, analysis_summary)
    if context_triage and isinstance(raw, dict):
        if str(raw.get("urgency_tier", "unclear")).strip().lower() in {"", "unclear"}:
            raw["urgency_tier"] = context_triage.urgency_tier
        raw.setdefault("info_sufficient", context_triage.info_sufficient)
        raw.setdefault("needs_helpline_first", context_triage.needs_helpline_first)
    return _normalize_response_payload(raw, emotion_result, condition_result, language)


def generate_fast_empathetic_response(
    emotion_result: dict,
    condition_result: dict,
    language: str = "en",
    user_context: str | None = None,
) -> dict:
    """Build a fast non-LLM analysis payload for upload flows.

    The analyze endpoint must return quickly; richer free-form guidance belongs
    in chat. This keeps the upload path to one vision call plus local shaping.
    """
    payload = _fallback_response(emotion_result, condition_result, language)
    context_triage = heuristic_classify_situation(user_context or "") if user_context else None
    if not context_triage:
        return payload

    context_text = (user_context or "").lower()
    if context_triage.scenario_type == "unclear" and any(
        phrase in context_text for phrase in ["hit by a car", "road accident", "vehicle hit", "car hit"]
    ):
        context_triage.scenario_type = "road_trauma"
        context_triage.urgency_tier = "life_threatening" if "cannot stand" in context_text else "urgent"
        context_triage.needs_helpline_first = True

    payload["urgency_tier"] = context_triage.urgency_tier
    payload["info_sufficient"] = context_triage.info_sufficient
    payload["needs_helpline_first"] = context_triage.needs_helpline_first

    if not context_triage.info_sufficient:
        if language == "hi":
            payload["triage_questions"] = [
                "क्या कुत्ता सामान्य सांस ले रहा है और प्रतिक्रिया दे रहा है?",
                "अभी मुख्य समस्या क्या दिख रही है?",
            ]
        elif language == "mr":
            payload["triage_questions"] = [
                "कुत्रा नीट श्वास घेतोय आणि प्रतिसाद देतोय का?",
                "आत्ता मुख्य त्रास काय दिसतोय?",
            ]
        else:
            payload["triage_questions"] = [
                "Is the dog breathing normally and responding?",
                "What is the main symptom or recent event?",
            ]
        payload["first_aid_steps"] = []
        payload["safety_level"] = "caution"
        return payload

    if context_triage.urgency_tier in {"life_threatening", "urgent"}:
        payload["safety_level"] = "danger" if context_triage.urgency_tier == "life_threatening" else "caution"

    if context_triage.scenario_type in {"road_trauma", "fracture"}:
        if language == "hi":
            payload["safety_reason"] = "\u091a\u094b\u091f \u092f\u093e \u0905\u092a\u0918\u093e\u0924 \u0915\u0947 \u092c\u093e\u0926 \u0926\u0930\u094d\u0926, \u092b\u094d\u0930\u0948\u0915\u094d\u091a\u0930 \u092f\u093e \u0905\u0902\u0926\u0930\u0942\u0928\u0940 \u091a\u094b\u091f \u0915\u093e \u0916\u0924\u0930\u093e \u0939\u094b \u0938\u0915\u0924\u093e \u0939\u0948\u0964"
            payload["empathetic_summary"] = "\u0907\u0938\u0947 \u0917\u0902\u092d\u0940\u0930 \u092e\u093e\u0928\u0947\u0902\u0964 \u0915\u0941\u0924\u094d\u0924\u0947 \u0915\u094b \u091a\u0932\u093e\u090f\u0902 \u0928\u0939\u0940\u0902, \u0936\u093e\u0902\u0924 \u0930\u0916\u0947\u0902, \u0914\u0930 \u092a\u0936\u0941-\u091a\u093f\u0915\u093f\u0924\u094d\u0938\u0915 \u092f\u093e \u0930\u0947\u0938\u094d\u0915\u094d\u092f\u0942 \u092e\u0926\u0926 \u091c\u0932\u094d\u0926\u0940 \u0932\u0947\u0902\u0964"
        elif language == "mr":
            payload["safety_reason"] = "\u0905\u092a\u0918\u093e\u0924\u093e\u0928\u0902\u0924\u0930 \u0935\u0947\u0926\u0928\u093e, \u092b\u094d\u0930\u0945\u0915\u094d\u091a\u0930 \u0915\u093f\u0902\u0935\u093e \u0905\u0902\u0924\u0930\u094d\u0917\u0924 \u091c\u0916\u092e\u0947\u091a\u093e \u0927\u094b\u0915\u093e \u0905\u0938\u0942 \u0936\u0915\u0924\u094b\u0964"
            payload["empathetic_summary"] = "\u0939\u0940 \u0917\u0902\u092d\u0940\u0930 \u0938\u094d\u0925\u093f\u0924\u0940 \u092e\u093e\u0928\u093e\u0964 \u0915\u0941\u0924\u094d\u0930\u094d\u092f\u093e\u0932\u093e \u091a\u093e\u0932\u0935\u0942 \u0928\u0915\u093e, \u0936\u093e\u0902\u0924 \u0920\u0947\u0935\u093e, \u0906\u0923\u093f \u092a\u0936\u0941\u0935\u0948\u0926\u094d\u092f \u0915\u093f\u0902\u0935\u093e \u0930\u0947\u0938\u094d\u0915\u094d\u092f\u0942 \u092e\u0926\u0924 \u0932\u0935\u0915\u0930 \u0918\u094d\u092f\u093e\u0964"
        else:
            payload["safety_reason"] = "After a road accident or suspected fracture, pain, shock, or internal injury is possible."
            payload["empathetic_summary"] = "Treat this as serious. Do not make the dog walk; keep them still and arrange veterinary or rescue help quickly."
        if language == "hi":
            payload["first_aid_steps"] = [
                {"step_number": 1, "instruction": "\u0915\u0941\u0924\u094d\u0924\u0947 \u0915\u094b \u091c\u093f\u0924\u0928\u093e \u0939\u094b \u0938\u0915\u0947 \u0938\u094d\u0925\u093f\u0930 \u0930\u0916\u0947\u0902; \u092a\u0948\u0930 \u092f\u093e \u0930\u0940\u0922\u093c \u0915\u094b \u0928 \u0916\u0940\u0902\u091a\u0947\u0902\u0964"},
                {"step_number": 2, "instruction": "\u092e\u0926\u0926 \u0939\u094b \u0924\u094b \u092c\u094b\u0930\u094d\u0921, \u0915\u0902\u092c\u0932 \u092f\u093e \u0915\u093f\u0938\u0940 \u0938\u0916\u094d\u0924 \u0938\u0924\u0939 \u092a\u0930 \u0932\u0947 \u091c\u093e\u090f\u0902\u0964"},
                {"step_number": 3, "instruction": "\u0909\u0930\u094d\u091c\u0947\u0902\u091f \u0926\u0947\u0916\u092d\u093e\u0932 \u0915\u093e \u0907\u0902\u0924\u091c\u093e\u092e \u0915\u0930\u0924\u0947 \u0939\u0941\u090f \u0938\u093e\u0902\u0938 \u0914\u0930 \u092e\u0938\u0942\u0921\u093c\u094b\u0902 \u0915\u093e \u0930\u0902\u0917 \u0926\u0947\u0916\u0924\u0947 \u0930\u0939\u0947\u0902\u0964"},
            ]
        elif language == "mr":
            payload["first_aid_steps"] = [
                {"step_number": 1, "instruction": "\u0915\u0941\u0924\u094d\u0930\u094d\u092f\u093e\u0932\u093e \u0936\u0915\u094d\u092f \u0924\u093f\u0924\u0915\u0947 \u0938\u094d\u0925\u093f\u0930 \u0920\u0947\u0935\u093e; \u092a\u093e\u092f \u0915\u093f\u0902\u0935\u093e \u092a\u093e\u0920\u0940\u091a\u093e \u0915\u0923\u093e \u0913\u0922\u0942 \u0928\u0915\u093e\u0964"},
                {"step_number": 2, "instruction": "\u092e\u0926\u0924 \u0905\u0938\u0947\u0932 \u0924\u0930 \u092c\u094b\u0930\u094d\u0921, \u092c\u094d\u0932\u0945\u0902\u0915\u0947\u091f \u0915\u093f\u0902\u0935\u093e \u0918\u091f\u094d\u091f \u092a\u0943\u0937\u094d\u0920\u092d\u093e\u0917\u093e\u0935\u0930 \u0935\u093e\u0939\u0924\u0942\u0915 \u0915\u0930\u093e\u0964"},
                {"step_number": 3, "instruction": "\u0924\u093e\u0924\u0921\u0940\u091a\u0940 \u0915\u093e\u0933\u091c\u0940 \u0920\u0930\u0935\u0924\u093e\u0928\u093e \u0936\u094d\u0935\u093e\u0938 \u0906\u0923\u093f \u0939\u093f\u0930\u0921\u094d\u092f\u093e\u0902\u091a\u093e \u0930\u0902\u0917 \u092a\u093e\u0939\u0924 \u0930\u0939\u093e\u0964"},
            ]
        else:
            payload["first_aid_steps"] = [
                {"step_number": 1, "instruction": "Keep the dog as still as possible and avoid pulling injured legs or the spine."},
                {"step_number": 2, "instruction": "Use a board, blanket, or firm surface for transport if help is available."},
                {"step_number": 3, "instruction": "Watch breathing and gum color while arranging urgent care."},
            ]

    if context_triage.scenario_type == "poisoning":
        payload["safety_level"] = "danger"
        if language == "hi":
            payload["safety_reason"] = "\u091c\u0939\u0930 \u092f\u093e \u0917\u0932\u0924 \u0926\u0935\u093e \u0915\u093e \u0936\u0915 \u0924\u0941\u0930\u0902\u0924 \u092e\u0926\u0926 \u092e\u093e\u0902\u0917\u0924\u093e \u0939\u0948\u0964"
            payload["empathetic_summary"] = "\u0909\u0932\u094d\u091f\u0940 \u0915\u0930\u093e\u0928\u0947 \u0915\u0940 \u0915\u094b\u0936\u093f\u0936 \u0928 \u0915\u0930\u0947\u0902\u0964 \u091c\u094b \u0916\u093e\u092f\u093e \u0939\u094b \u0909\u0938\u0915\u093e \u092a\u0948\u0915\u0947\u091f \u092f\u093e \u0928\u093e\u092e \u0938\u093e\u0925 \u0930\u0916\u0947\u0902 \u0914\u0930 \u0924\u0941\u0930\u0902\u0924 \u0935\u0947\u091f/\u0930\u0947\u0938\u094d\u0915\u094d\u092f\u0942 \u0938\u0947 \u092c\u093e\u0924 \u0915\u0930\u0947\u0902\u0964"
        elif language == "mr":
            payload["safety_reason"] = "\u0935\u093f\u0937 \u0915\u093f\u0902\u0935\u093e \u091a\u0941\u0915\u0940\u091a\u094d\u092f\u093e \u0914\u0937\u0927\u093e\u091a\u093e \u0936\u0902\u0915\u093e \u0905\u0938\u0947\u0932 \u0924\u0930 \u0924\u093e\u0924\u0921\u0940\u0928\u0947 \u092e\u0926\u0924 \u0932\u093e\u0917\u0924\u0947\u0964"
            payload["empathetic_summary"] = "\u0909\u0932\u091f\u0940 \u0915\u0930\u093e\u092f\u091a\u093e \u092a\u094d\u0930\u092f\u0924\u094d\u0928 \u0915\u0930\u0942 \u0928\u0915\u093e\u0964 \u091c\u0947 \u0916\u093e\u0932\u094d\u0932\u0947 \u0905\u0938\u0947\u0932 \u0924\u094d\u092f\u093e\u091a\u0947 \u0928\u093e\u0935 \u0915\u093f\u0902\u0935\u093e \u092a\u0945\u0915\u0947\u091f \u091c\u0935\u0933 \u0920\u0947\u0935\u093e \u0906\u0923\u093f \u0924\u0941\u0930\u0902\u0924 \u0935\u0947\u091f/\u0930\u0947\u0938\u094d\u0915\u094d\u092f\u0942\u0936\u0940 \u092c\u094b\u0932\u093e\u0964"
        else:
            payload["safety_reason"] = "Possible poisoning or unsafe medicine exposure needs urgent advice."
            payload["empathetic_summary"] = "Do not try to make the dog vomit. Keep the package or substance name and call a vet or rescue line now."
        if language == "hi":
            payload["first_aid_steps"] = [
                {"step_number": 1, "instruction": "\u0905\u0917\u0930 \u0938\u0941\u0930\u0915\u094d\u0937\u093f\u0924 \u0939\u094b \u0924\u094b \u0915\u0941\u0924\u094d\u0924\u0947 \u0915\u094b \u0936\u0915 \u0935\u093e\u0932\u0947 \u091c\u0939\u0930 \u0938\u0947 \u0926\u0942\u0930 \u0915\u0930\u0947\u0902\u0964"},
                {"step_number": 2, "instruction": "\u091c\u092c\u0930\u0926\u0938\u094d\u0924\u0940 \u0909\u0932\u094d\u091f\u0940, \u0926\u0942\u0927, \u0924\u0947\u0932 \u092f\u093e \u0918\u0930\u0947\u0932\u0942 \u0928\u0941\u0938\u094d\u0916\u0947 \u0928 \u0926\u0947\u0902\u0964"},
                {"step_number": 3, "instruction": "\u0935\u0947\u091f/\u0930\u0947\u0938\u094d\u0915\u094d\u092f\u0942 \u0932\u093e\u0907\u0928 \u0915\u094b \u092a\u0926\u093e\u0930\u094d\u0925 \u0915\u093e \u0928\u093e\u092e, \u092e\u093e\u0924\u094d\u0930\u093e \u0914\u0930 \u0938\u092e\u092f \u092c\u0924\u093e\u090f\u0902\u0964"},
            ]
        elif language == "mr":
            payload["first_aid_steps"] = [
                {"step_number": 1, "instruction": "\u0938\u0941\u0930\u0915\u094d\u0937\u093f\u0924 \u0905\u0938\u0947\u0932 \u0924\u0930 \u0915\u0941\u0924\u094d\u0930\u094d\u092f\u093e\u0932\u093e \u0938\u0902\u0936\u092f\u093f\u0924 \u0935\u093f\u0937\u093e\u092a\u093e\u0938\u0942\u0928 \u0926\u0942\u0930 \u0915\u0930\u093e\u0964"},
                {"step_number": 2, "instruction": "\u091c\u092c\u0930\u0926\u0938\u094d\u0924\u0940 \u0909\u0932\u091f\u0940, \u0926\u0942\u0927, \u0924\u0947\u0932 \u0915\u093f\u0902\u0935\u093e \u0918\u0930\u0917\u0941\u0924\u0940 \u0909\u092a\u093e\u092f \u0926\u0947\u090a \u0928\u0915\u093e\u0964"},
                {"step_number": 3, "instruction": "\u0935\u0947\u091f/\u0930\u0947\u0938\u094d\u0915\u094d\u092f\u0942 \u0932\u093e\u0907\u0928\u0932\u093e \u092a\u0926\u093e\u0930\u094d\u0925\u093e\u091a\u0947 \u0928\u093e\u0935, \u092a\u094d\u0930\u092e\u093e\u0923 \u0906\u0923\u093f \u0935\u0947\u0933 \u0938\u093e\u0902\u0917\u093e\u0964"},
            ]
        else:
            payload["first_aid_steps"] = [
                {"step_number": 1, "instruction": "Move the dog away from the suspected poison if you can do so safely."},
                {"step_number": 2, "instruction": "Do not force vomiting, milk, oil, or home remedies."},
                {"step_number": 3, "instruction": "Contact a vet/rescue line with the substance name, amount, and time eaten."},
            ]

    if context_triage.scenario_type == "fall_entrapment":
        if language == "hi":
            payload["safety_reason"] = "कुत्ता गहरे या बंद स्थान में फंसा हो सकता है; बचाव उपकरण की जरूरत पड़ सकती है।"
            payload["empathetic_summary"] = "यह आपात स्थिति है। पहले बचाव सहायता बुलाएं और किनारे पर भीड़ न लगने दें।"
            payload["first_aid_steps"] = [
                {"step_number": 1, "instruction": "अभी स्थानीय रेस्क्यू/फायर सेवा को कॉल करें।"},
                {"step_number": 2, "instruction": "खुद कुएं में न उतरें और लोगों को किनारे से दूर रखें।"},
                {"step_number": 3, "instruction": "ऊपर से शांत आवाज में कुत्ते पर नजर रखें।"},
            ]
        elif language == "mr":
            payload["safety_reason"] = "कुत्रा खोल किंवा बंद जागेत अडकला असू शकतो; बचाव साधनांची गरज लागू शकते."
            payload["empathetic_summary"] = "ही आपत्कालीन स्थिती आहे. आधी बचाव मदत बोलवा आणि काठाजवळ गर्दी होऊ देऊ नका."
            payload["first_aid_steps"] = [
                {"step_number": 1, "instruction": "आत्ताच स्थानिक रेस्क्यू/फायर सेवेला कॉल करा."},
                {"step_number": 2, "instruction": "स्वतः विहिरीत उतरू नका आणि लोकांना काठापासून दूर ठेवा."},
                {"step_number": 3, "instruction": "वरून शांत आवाजात कुत्र्यावर लक्ष ठेवा."},
            ]
        else:
            payload["safety_reason"] = "The dog may be trapped in a deep or confined space and may need rescue equipment."
            payload["empathetic_summary"] = "This is an emergency. Call rescue help first and keep people back from the edge."
            payload["first_aid_steps"] = [
                {"step_number": 1, "instruction": "Call local rescue/fire services now."},
                {"step_number": 2, "instruction": "Do not climb into the well; keep bystanders away from the edge."},
                {"step_number": 3, "instruction": "Watch breathing and movement from above while help is coming."},
            ]
        payload["when_to_call_professional"] = ""

    if context_triage.urgency_tier == "life_threatening":
        payload["first_aid_steps"] = payload.get("first_aid_steps", [])[:3]

    return payload


async def _translate_payload_once(source_payload: dict, language: str, repair: bool = False) -> dict | None:
    language_name = TRANSLATION_INSTRUCTIONS.get(language)
    if not language_name:
        return None

    prompt = TRANSLATION_REPAIR_SYSTEM_PROMPT if repair else TRANSLATION_SYSTEM_PROMPT
    return await _call_groq_json(
        prompt.format(language_name=language_name),
        json.dumps(source_payload, ensure_ascii=False),
        max_tokens=1400,
    )


async def translate_analysis_payload(source_payload: dict, language: str) -> dict:
    """Translate a canonical English analysis payload into a UI-ready language payload."""
    if language == "en":
        return {
            "condition": source_payload["condition"],
            "safety_level": source_payload["safety_level"],
            "safety_reason": source_payload["safety_reason"],
            "empathetic_summary": source_payload["empathetic_summary"],
            "first_aid_steps": source_payload["first_aid_steps"],
            "triage_questions": source_payload.get("triage_questions", []),
            "when_to_call_professional": source_payload["when_to_call_professional"],
            "approach_tips": source_payload["approach_tips"],
            "disclaimer": DISCLAIMERS["en"],
        }

    if language not in TRANSLATION_INSTRUCTIONS:
        return {
            "condition": source_payload["condition"],
            "safety_level": source_payload["safety_level"],
            "safety_reason": source_payload["safety_reason"],
            "empathetic_summary": source_payload["empathetic_summary"],
            "first_aid_steps": source_payload["first_aid_steps"],
            "triage_questions": source_payload.get("triage_questions", []),
            "when_to_call_professional": source_payload["when_to_call_professional"],
            "approach_tips": source_payload["approach_tips"],
            "disclaimer": DISCLAIMERS["en"],
        }

    translation_source = {
        "condition": source_payload["condition"],
        "safety_reason": source_payload["safety_reason"],
        "empathetic_summary": source_payload["empathetic_summary"],
        "first_aid_steps": source_payload["first_aid_steps"],
        "triage_questions": source_payload.get("triage_questions", []),
        "when_to_call_professional": source_payload["when_to_call_professional"],
        "approach_tips": source_payload["approach_tips"],
    }
    raw = await _translate_payload_once(translation_source, language, repair=False)
    if not _translation_coverage_ok(raw, language):
        logger.warning("Translation for %s left English text; retrying strict repair.", language)
        repaired = await _translate_payload_once(translation_source, language, repair=True)
        if _translation_coverage_ok(repaired, language):
            raw = repaired

    return _normalize_translated_payload(raw, source_payload, language)
