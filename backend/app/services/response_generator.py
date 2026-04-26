"""Empathetic response and translation helpers for analysis results."""

import json
import logging
import re

import httpx

from app.config import get_settings
from app.services.groq_retry import groq_post_with_retry

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
  "when_to_call_professional": "one sentence about when professional help is needed",
  "approach_tips": "one or two sentences on how to approach the dog safely"
}}

Rules:
- Safety level must match the dog's visible behavior and injuries
- Translate the provided condition facts into the target language without changing the underlying meaning
- Keep first aid steps simple for a non-expert
- Use 3 to 5 first aid steps
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


def _normalize_first_aid_steps(raw_steps: object, fallback_steps: list[dict]) -> list[dict]:
    if not isinstance(raw_steps, list) or not raw_steps:
        return fallback_steps

    normalized: list[dict] = []
    for index, fallback_step in enumerate(fallback_steps):
        raw_step = raw_steps[index] if index < len(raw_steps) else None
        instruction = fallback_step["instruction"]
        if isinstance(raw_step, dict):
            instruction = _clean_text(raw_step.get("instruction"), instruction)
        normalized.append(
            {
                "step_number": fallback_step["step_number"],
                "instruction": instruction,
            }
        )
    return normalized


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


def _fallback_response(emotion_result: dict, condition_result: dict, language: str) -> dict:
    emotion_label = str(emotion_result.get("label", "unknown")).strip().lower()
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

    return {
        "condition": normalized_condition,
        "safety_level": safety_level,
        "safety_reason": _clean_text(raw.get("safety_reason"), fallback["safety_reason"]),
        "empathetic_summary": _clean_text(raw.get("empathetic_summary"), fallback["empathetic_summary"]),
        "first_aid_steps": _normalize_first_aid_steps(raw.get("first_aid_steps"), fallback["first_aid_steps"]),
        "when_to_call_professional": _clean_text(
            raw.get("when_to_call_professional"),
            fallback["when_to_call_professional"],
        ),
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
    analysis_summary += LANGUAGE_REMINDERS.get(language, "")

    raw = await _call_groq_json(system_prompt, analysis_summary)
    return _normalize_response_payload(raw, emotion_result, condition_result, language)


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
            "when_to_call_professional": source_payload["when_to_call_professional"],
            "approach_tips": source_payload["approach_tips"],
            "disclaimer": DISCLAIMERS["en"],
        }

    translation_source = {
        "condition": source_payload["condition"],
        "safety_reason": source_payload["safety_reason"],
        "empathetic_summary": source_payload["empathetic_summary"],
        "first_aid_steps": source_payload["first_aid_steps"],
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
