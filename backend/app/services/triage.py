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
_VALID_MODES = frozenset({"warm", "care", "emergency", "repair"})
_DEVANAGARI_WARM = frozenset(["नमस्ते", "नमस्कार", "हाय", "हेलो", "सुप्रभात", "शुभ संध्या"])

LOCAL_DECISION_SCENARIOS = {
    "fall_entrapment",
    "choking_airway",
    "seizure_collapse",
    "severe_bleeding",
    "heatstroke",
    "road_trauma",
    "poisoning",
    "rabies_exposure",
    "conversation_repair",
    "warm_conversation",
    "symptom_negated",
    "mild_behavior_change",
    "no_dog_visible",
    "deceased_pet",
    "animal_cruelty_witnessed",
    "feeding_weak_dog",
    "unsafe_medicine",
    "unsafe_home_remedy",
}

CANONICAL_SCENARIOS = {
    "fall_entrapment",
    "choking_airway",
    "seizure_collapse",
    "severe_bleeding",
    "heatstroke",
    "road_trauma",
    "poisoning",
    "rabies_exposure",
    "fracture",
    "maggot_wound",
    "skin_disease",
    "tick_infestation",
    "puppy_gi",
    "eye_injury",
    "fearful_aggressive",
    "injured_transport",
    "burn_injury",
    "vomiting_diarrhea",
    "lost_dog",
    "feeding_weak_dog",
    "routine_care",
    "unsafe_medicine",
    "unsafe_home_remedy",
    "deceased_pet",
    "healthy_or_low_risk",
    "no_dog_visible",
    "animal_cruelty_witnessed",
    "conversation_repair",
    "warm_conversation",
    "symptom_negated",
    "mild_behavior_change",
    "unclear",
}

SCENARIO_ALIASES = {
    "abuse": "animal_cruelty_witnessed",
    "animal_abuse": "animal_cruelty_witnessed",
    "animal_cruelty": "animal_cruelty_witnessed",
    "bleeding": "severe_bleeding",
    "diarrhea": "vomiting_diarrhea",
    "diarrhoea": "vomiting_diarrhea",
    "feeding": "feeding_weak_dog",
    "feeding_question": "feeding_weak_dog",
    "gastroenteritis": "vomiting_diarrhea",
    "gastrointestinal": "vomiting_diarrhea",
    "gastrointestinal_issue": "vomiting_diarrhea",
    "general_health": "healthy_or_low_risk",
    "gi": "vomiting_diarrhea",
    "gi_issue": "vomiting_diarrhea",
    "healthy": "healthy_or_low_risk",
    "healthy_low_risk": "healthy_or_low_risk",
    "human_medicine": "unsafe_medicine",
    "leg_injury": "fracture",
    "limb_injury": "fracture",
    "limping": "fracture",
    "medicine": "unsafe_medicine",
    "medicine_question": "unsafe_medicine",
    "otc_medicine": "unsafe_medicine",
    "puppy_diarrhea": "puppy_gi",
    "puppy_diarrhoea": "puppy_gi",
    "puppy_vomiting": "puppy_gi",
    "weak_puppy": "feeding_weak_dog",
}

VALID_INTENTS = {"general", "medicine_question", "cruelty_witnessed"}


class TriageResult(BaseModel):
    urgency_tier: str = "unclear"
    info_sufficient: bool = False
    missing_facts: list[str] = Field(default_factory=list)
    scenario_type: str = "unclear"
    needs_helpline_first: bool = False
    rationale: str = ""
    mode: str = "care"
    context_used: bool = False
    intent: str = "general"


TRIAGE_SYSTEM_PROMPT = """You classify urgent dog rescue / first-aid chat messages.

Return ONLY valid JSON:
{
  "urgency_tier": "life_threatening" | "urgent" | "moderate" | "low_risk" | "unclear",
  "info_sufficient": true | false,
  "missing_facts": ["short_snake_case_fact"],
  "scenario_type": "short_snake_case",
  "needs_helpline_first": true | false,
  "rationale": "one short line",
  "mode": "warm" | "care" | "emergency" | "repair",
  "intent": "general" | "medicine_question" | "cruelty_witnessed"
}

Rules:
- mode "warm": greetings, dog introductions, healthy-dog curiosity, breed questions, no symptom present.
- mode "care": any symptom, concern, or care question that is not an emergency.
- mode "emergency": life_threatening urgency tier; requires immediate action.
- mode "repair": user is correcting or redirecting the conversation, not reporting a new situation.
- Use intent "cruelty_witnessed" and scenario_type "animal_cruelty_witnessed" when the user is reporting abuse, poisoning, beating, illegal relocation, abandonment, or neglect by people against a stray/community animal.
- Use intent "medicine_question" for asks about medicines, painkillers, OTC treatments, toxins, or unsafe human medicines.
- Mark life_threatening for entrapment in wells/pits/drains, drowning, choking, not breathing, collapse, repeated seizure, heavy bleeding, heatstroke collapse, major road trauma, suspected spinal injury, severe poisoning signs.
- Mark needs_helpline_first true when the scene needs rescue equipment or urgent dispatch: well/pit/drain/pipe entrapment, drowning, major road accident, trapped under vehicle, roof/height rescue, aggressive dog endangering people.
- If the message is vague ("acting weird", "not ok", "help") and no analysis context gives specifics, set info_sufficient false and ask for the few missing facts needed to choose safe first aid.
- Do not make info_sufficient false just because the city, exact age, or depth is unknown when the immediate hazard is already clear.
- Use the closest canonical scenario_type: fall_entrapment, choking_airway, poisoning, heatstroke, road_trauma, fracture, severe_bleeding, seizure_collapse, maggot_wound, skin_disease, tick_infestation, puppy_gi, eye_injury, fearful_aggressive, injured_transport, burn_injury, vomiting_diarrhea, lost_dog, feeding_weak_dog, routine_care, unsafe_medicine, unsafe_home_remedy, deceased_pet, healthy_or_low_risk, no_dog_visible, animal_cruelty_witnessed, warm_conversation, conversation_repair, symptom_negated, mild_behavior_change, unclear.
- Classify correctly for English, Hindi, Marathi, and code-mixed messages. Output fields are language-neutral.
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


def _canonicalize_scenario(raw_value: object, fallback: TriageResult) -> str:
    scenario_type = re.sub(
        r"[^a-z0-9_]+",
        "_",
        str(raw_value or fallback.scenario_type).strip().lower(),
    ).strip("_") or fallback.scenario_type
    scenario_type = SCENARIO_ALIASES.get(scenario_type, scenario_type)

    if fallback.scenario_type == "warm_conversation" and scenario_type in {
        "healthy_or_low_risk",
        "routine_care",
        "unclear",
    }:
        return "warm_conversation"
    if fallback.scenario_type == "conversation_repair" and scenario_type in {
        "healthy_or_low_risk",
        "routine_care",
        "unclear",
    }:
        return "conversation_repair"

    if scenario_type in CANONICAL_SCENARIOS:
        return scenario_type
    if fallback.scenario_type in CANONICAL_SCENARIOS:
        return fallback.scenario_type
    return "unclear"


def _normalize_result(raw: dict | None, fallback: TriageResult) -> TriageResult:
    if not isinstance(raw, dict):
        return fallback

    urgency_tier = str(raw.get("urgency_tier", fallback.urgency_tier)).strip().lower()
    if urgency_tier not in URGENCY_TIERS:
        urgency_tier = fallback.urgency_tier

    scenario_type = _canonicalize_scenario(raw.get("scenario_type"), fallback)

    raw_mode = str(raw.get("mode", "")).strip().lower()
    if raw_mode not in _VALID_MODES:
        raw_mode = fallback.mode
    raw_intent = re.sub(
        r"[^a-z0-9_]+",
        "_",
        str(raw.get("intent", fallback.intent)).strip().lower(),
    ).strip("_") or fallback.intent
    if raw_intent not in VALID_INTENTS:
        raw_intent = fallback.intent
    if raw_intent == "general" and fallback.intent != "general":
        raw_intent = fallback.intent
    if scenario_type == "unsafe_medicine":
        raw_intent = "medicine_question"
    if scenario_type == "animal_cruelty_witnessed":
        raw_intent = "cruelty_witnessed"

    # Safety overrides: deterministic gates cannot be downgraded by the LLM
    if fallback.urgency_tier == "life_threatening":
        urgency_tier = "life_threatening"
        raw_mode = "emergency"
    if fallback.scenario_type == "conversation_repair":
        scenario_type = "conversation_repair"
        raw_mode = "repair"
    if fallback.scenario_type == "warm_conversation":
        scenario_type = "warm_conversation"
        raw_mode = "warm"
    if urgency_tier == "life_threatening":
        raw_mode = "emergency"
    if scenario_type == "conversation_repair":
        raw_mode = "repair"
    if scenario_type == "warm_conversation":
        raw_mode = "warm"

    return TriageResult(
        urgency_tier=urgency_tier,
        info_sufficient=bool(raw.get("info_sufficient", fallback.info_sufficient)),
        missing_facts=_normalize_string_list(raw.get("missing_facts")) or fallback.missing_facts,
        scenario_type=scenario_type,
        needs_helpline_first=bool(raw.get("needs_helpline_first", fallback.needs_helpline_first)),
        rationale=str(raw.get("rationale", fallback.rationale)).strip()[:220],
        mode=raw_mode,
        context_used=fallback.context_used,
        intent=raw_intent,
    )


def _derive_mode(urgency_tier: str, scenario_type: str) -> str:
    if scenario_type == "conversation_repair":
        return "repair"
    if scenario_type == "warm_conversation":
        return "warm"
    if urgency_tier == "life_threatening":
        return "emergency"
    return "care"


def _contains_any(text: str, patterns: list[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def _normalize_turn_text(text: str) -> str:
    normalized = text.lower()
    for old, new in {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
    }.items():
        normalized = normalized.replace(old, new)
    return normalized


def _is_context_dependent(user_message: str) -> bool:
    text = re.sub(r"\s+", " ", _normalize_turn_text(user_message)).strip()
    if not text:
        return False

    dependent_phrases = [
        "what should i do",
        "what do i do",
        "what next",
        "next step",
        "next steps",
        "is it urgent",
        "is this urgent",
        "same dog",
        "this dog",
        "the dog",
        "that dog",
        "photo",
        "image",
        "analysis",
        "above",
    ]
    if _contains_any(text, dependent_phrases):
        return True

    words = text.split()
    pronouns = {"it", "he", "she", "him", "her", "they", "them", "this", "that"}
    generic_help = {"help", "now", "next", "urgent"}
    return len(words) <= 8 and bool(set(words) & pronouns) and bool(set(words) & generic_help)


def _strip_negated_emergency_terms(text: str) -> str:
    stripped = text
    negated_patterns = [
        r"\bno\s+(?:seizure|seizures|seizing|bleeding|blood|choking|dehydration|vomiting|vomit|diarrhea|diarrhoea)\b",
        r"\bnot\s+(?:seizing|bleeding|choking|dehydrated|vomiting|limping|collapsed|unconscious)\b",
        r"\b(?:isn't|isnt|wasn't|wasnt)\s+(?:seizing|bleeding|choking|dehydrated|vomiting|limping|collapsed|unconscious)\b",
        r"\bwithout\s+(?:bleeding|blood|vomiting|diarrhea|diarrhoea|dehydration)\b",
        r"\bbreathing\s+(?:fine|normally|normal|ok|okay)\b",
        r"\bcan\s+(?:breathe|breath|walk|stand)\b",
        r"\bblood\s+stopped\b",
    ]
    for pattern in negated_patterns:
        stripped = re.sub(pattern, " ", stripped)
    return re.sub(r"\s+", " ", stripped).strip()


ACTIVE_CARE_TERMS = [
    "accident",
    "bleed",
    "blood",
    "broken",
    "can't breathe",
    "can't stand",
    "can't walk",
    "cannot breathe",
    "cannot stand",
    "cannot walk",
    "choking",
    "chocolate",
    "collapse",
    "collapsed",
    "diarrhea",
    "diarrhoea",
    "dying",
    "feed",
    "fracture",
    "hit by",
    "hungry",
    "injured",
    "kamjor",
    "kamzor",
    "khilana",
    "khilao",
    "khilau",
    "limp",
    "maggot",
    "medicine",
    "not drinking",
    "not eating",
    "pain",
    "poison",
    "pup",
    "puppy",
    "seizure",
    "sick",
    "tablet",
    "tick",
    "unwell",
    "vomit",
    "weak",
    "wound",
    "xylitol",
]


def _has_active_care_signal(text: str) -> bool:
    normalized = re.sub(r"[^a-z0-9\s']+", " ", _normalize_turn_text(text))
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return _contains_any(normalized, ACTIVE_CARE_TERMS)


def _is_repair_or_meta_intent(text: str) -> bool:
    normalized = re.sub(r"[^a-z0-9\s']+", " ", _normalize_turn_text(text))
    normalized = re.sub(r"\s+", " ", normalized).strip()
    hard_repair_patterns = [
        "stop repeating",
        "you are repeating",
        "you're repeating",
        "why did you say",
        "that is wrong",
        "that's wrong",
        "you got it wrong",
        "not what i asked",
        "not that",
        "you misunderstood",
        "not an emergency",
        "not emergency",
    ]
    redirect_patterns = [
        "new topic",
        "different dog",
        "different puppy",
        "different animal",
        "forget that",
        "reset",
    ]
    if _contains_any(text, hard_repair_patterns) or _contains_any(normalized, hard_repair_patterns):
        return True
    if (
        _contains_any(text, redirect_patterns) or _contains_any(normalized, redirect_patterns)
    ) and not _has_active_care_signal(normalized):
        return True
    hindi_marathi_repair = [
        "यह गलत है",
        "ये गलत है",
        "बार बार मत",
        "बार-बार मत",
        "हे चुकीचे",
        "परत परत सांगू नकोस",
        "मैंने यह नहीं पूछा",
    ]
    return _contains_any(text, hindi_marathi_repair)


def _is_emotional_check_in(text: str) -> bool:
    normalized = re.sub(r"[^a-z0-9\s']+", " ", _normalize_turn_text(text))
    normalized = re.sub(r"\s+", " ", normalized).strip()
    emotional_patterns = [
        "i am anxious",
        "i am just anxious",
        "i get anxious",
        "i get really worried",
        "i just worry",
        "i worry a lot",
        "i'm anxious",
        "sorry for asking",
        "sorry i ask",
        "sorry to ask",
        "thanks for answering",
        "thank you for answering",
    ]
    return _contains_any(normalized, emotional_patterns) and not _has_active_care_signal(normalized)


def _is_deceased_pet_context(text: str) -> bool:
    normalized = re.sub(r"[^a-z0-9'\s]+", " ", _normalize_turn_text(text))
    normalized = re.sub(r"\s+", " ", normalized).strip()

    if re.search(r"\b(?:not|isn't|isnt|wasn't|wasnt)\s+(?:dead|deceased)\b", normalized):
        return False
    if re.search(r"\b(?:alive|still alive)\b", normalized):
        return False

    if normalized in {"dead", "deceased", "died"}:
        return True

    death_patterns = [
        r"\b(?:dog|puppy|pup|pet|he|she|they|it)\s*(?:is|are|was|were|'s|'re)?\s*(?:just|already)?\s*(?:dead|deceased)\b",
        r"\b(?:my|this|that|the)\s+(?:dog|puppy|pup|pet)\s+(?:is|was|has)?\s*(?:dead|deceased|died)\b",
        r"\b(?:dog|puppy|pup|pet|he|she|they|it)\s+(?:died|passed away|has passed|had passed)\b",
        r"\b(?:passed away|has passed|had passed|no longer alive)\b",
        r"\b(?:mar gaya|mar gayi|mar gya|mar gyi|gujar gaya|gujar gayi|expired)\b",
    ]
    if any(re.search(pattern, normalized) for pattern in death_patterns):
        return True

    devanagari_death_patterns = [
        "मर गया",
        "मर गई",
        "मर गयी",
        "मृत",
        "गुज़र गया",
        "गुजर गया",
        "गुज़र गई",
        "गुजर गई",
        "मेला",
        "मेली",
        "मरण पावला",
        "मरण पावली",
        "निधन",
    ]
    return _contains_any(text, devanagari_death_patterns)


def _is_warm_conversation(text: str) -> bool:
    if text.strip() in _DEVANAGARI_WARM:
        return True
    normalized = re.sub(r"[^a-z0-9\s']+", " ", text.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if normalized in {"hi", "hello", "hey", "what's up", "whats up", "good morning", "good evening"}:
        return True
    warm_patterns = [
        "cute dog",
        "my dog is cute",
        "i have a dog",
        "i have an indie",
        "meet my dog",
        "look at my dog",
        "all good",
        "just saying hi",
    ]
    return _contains_any(normalized, warm_patterns)


def _is_cruelty_witnessed(text: str) -> bool:
    normalized = re.sub(r"[^a-z0-9\s']+", " ", _normalize_turn_text(text))
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if _contains_any(normalized, ["hit by car", "hit by bike", "road accident", "vehicle hit", "car hit"]):
        return False

    cruelty_patterns = [
        "animal cruelty",
        "cruelty",
        "abuse",
        "abusing",
        "beating stray",
        "beating a stray",
        "kicking stray",
        "someone hit a dog",
        "someone hit a cat",
        "someone poisoned",
        "poisoning stray",
        "throwing stones",
        "illegal relocation",
        "relocating dogs",
        "abandoned puppies",
        "neglecting animal",
        "tied without food",
        "kept without water",
    ]
    if _contains_any(normalized, cruelty_patterns):
        return True

    devanagari_patterns = [
        "क्रूरता",
        "जानवर को मार",
        "कुत्ते को मार",
        "बिल्ली को मार",
        "जहर दिया",
        "ज़हर दिया",
        "पत्थर मार",
        "बिना खाना",
        "बिना पानी",
        "प्राण्यांवर क्रूरता",
        "कुत्र्याला मार",
        "मांजरीला मार",
        "विष दिल",
        "दगड मार",
    ]
    return _contains_any(text, devanagari_patterns)


MEDICINE_TERMS = [
    "acetaminophen",
    "anti vomiting",
    "anti-vomiting",
    "aspirin",
    "betadine",
    "combiflam",
    "crocin",
    "electrolyte",
    "human medicine",
    "ibuprofen",
    "iodine",
    "nausea medicine",
    "oral rehydration",
    "ors",
    "pain killer",
    "painkiller",
    "paracetamol",
    "pedialyte",
    "povidone",
    "saline",
    "vomiting tablet",
    "wound wash",
]
GENERIC_MEDICINE_TERMS = ["dose", "medicine", "tablet"]
MEDICINE_ASK_TERMS = ["can i", "dose", "give", "gave", "given", "how much", "should i"]
TOXIN_TERMS = [
    "chocolate",
    "garlic",
    "grape",
    "grapes",
    "onion",
    "pesticide",
    "poison",
    "raisin",
    "raisins",
    "rat poison",
    "xylitol",
]
EXPOSURE_TERMS = [
    "ate",
    "chewed",
    "drank",
    "eaten",
    "fed",
    "gave",
    "given",
    "got into",
    "ingested",
    "licked",
    "swallowed",
]
HYPOTHETICAL_ASK_TERMS = [
    "can i",
    "could i",
    "feed",
    "give",
    "is it safe",
    "safe to",
    "should i",
    "what if",
]
PUPPY_TERMS = ["pup", "puppy", "puppies"]
WEAK_OR_FOUND_TERMS = [
    "bahut kamzor",
    "found",
    "kamjor",
    "kamzor",
    "malnourished",
    "mili",
    "nayi",
    "new puppy",
    "orphan",
    "skinny",
    "starving",
    "thin",
    "very weak",
    "weak",
]
FEEDING_TERMS = [
    "doodh",
    "duudh",
    "eat",
    "feed",
    "food",
    "formula",
    "hungry",
    "kya khil",
    "khilana",
    "khilao",
    "khilau",
    "milk",
]


def _is_medicine_question(text: str) -> bool:
    normalized = re.sub(r"[^a-z0-9\s'-]+", " ", _normalize_turn_text(text))
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return _contains_any(normalized, MEDICINE_TERMS) or (
        _contains_any(normalized, GENERIC_MEDICINE_TERMS)
        and _contains_any(normalized, MEDICINE_ASK_TERMS)
    )


def _has_toxin_exposure_cue(text: str) -> bool:
    normalized = re.sub(r"[^a-z0-9\s']+", " ", _normalize_turn_text(text))
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return any(re.search(rf"\b{re.escape(term)}\b", normalized) for term in EXPOSURE_TERMS)


def _is_hypothetical_toxin_question(text: str) -> bool:
    normalized = re.sub(r"[^a-z0-9\s']+", " ", _normalize_turn_text(text))
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return (
        _contains_any(normalized, TOXIN_TERMS)
        and not _has_toxin_exposure_cue(normalized)
        and _contains_any(normalized, HYPOTHETICAL_ASK_TERMS)
    )


def _is_weak_puppy_feeding_question(text: str) -> bool:
    normalized = re.sub(r"[^a-z0-9\s']+", " ", _normalize_turn_text(text))
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return (
        _contains_any(normalized, PUPPY_TERMS)
        and _contains_any(normalized, WEAK_OR_FOUND_TERMS)
        and _contains_any(normalized, FEEDING_TERMS)
    )


def _heuristic_classify_internal(
    user_message: str,
    analysis_context: str | None = None,
    last_assistant_message: str | None = None,
) -> TriageResult:
    """Deterministic fallback used when the model is unavailable.

    Assistant replies are intentionally ignored here. Generated warning text is
    conversation context for the model, not evidence for a new triage scenario.
    """
    del last_assistant_message
    user_compact = re.sub(r"\s+", " ", _normalize_turn_text(user_message)).strip()
    context = analysis_context if analysis_context and _is_context_dependent(user_message) else ""
    combined = " ".join(
        part for part in [user_message, context] if part
    )
    combined = _normalize_turn_text(combined)
    compact = re.sub(r"\s+", " ", combined).strip()
    screen_text = _strip_negated_emergency_terms(compact)

    if not compact:
        return TriageResult(
            info_sufficient=False,
            missing_facts=["what_happened", "current_symptoms"],
            rationale="No situation details were provided.",
        )

    if _is_deceased_pet_context(user_compact):
        return TriageResult(
            urgency_tier="low_risk",
            info_sufficient=True,
            scenario_type="deceased_pet",
            rationale="The user is talking about a dog who has already died, not an active emergency.",
        )

    if _is_emotional_check_in(user_compact):
        return TriageResult(
            urgency_tier="low_risk",
            info_sufficient=True,
            scenario_type="warm_conversation",
            rationale="The user is expressing worry or apology without a new symptom.",
        )

    if _is_repair_or_meta_intent(user_compact):
        return TriageResult(
            urgency_tier="low_risk",
            info_sufficient=True,
            scenario_type="conversation_repair",
            rationale="The user is correcting or steering the conversation, not reporting a new emergency.",
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

    if _is_warm_conversation(user_compact) and not _contains_any(
        screen_text,
        [
            "poison",
            "xylitol",
            "chocolate",
            "not breathing",
            "cannot breathe",
            "can't breathe",
            "choking",
            "bleeding",
            "blood",
            "collapse",
            "collapsed",
            "seizure",
            "hit by",
            "accident",
            "maggot",
            "diarrhea",
            "diarrhoea",
            "vomit",
            "wound",
        ],
    ):
        return TriageResult(
            urgency_tier="low_risk",
            info_sufficient=True,
            scenario_type="warm_conversation",
            rationale="The user is starting a normal friendly dog-care conversation.",
        )

    if _contains_any(compact, ["no dog", "dog is not visible", "no animal visible"]):
        return TriageResult(
            urgency_tier="low_risk",
            info_sufficient=True,
            scenario_type="no_dog_visible",
            rationale="The user says there is no visible dog to assess.",
        )

    if _is_cruelty_witnessed(user_compact):
        return TriageResult(
            urgency_tier="moderate",
            info_sufficient=True,
            scenario_type="animal_cruelty_witnessed",
            missing_facts=["location", "evidence_available", "animal_in_immediate_danger"],
            rationale="The user is reporting possible cruelty by people, which needs documentation and reporting guidance.",
            intent="cruelty_witnessed",
        )

    if _is_medicine_question(compact):
        return TriageResult(
            urgency_tier="urgent" if _has_toxin_exposure_cue(compact) else "moderate",
            info_sufficient=True,
            missing_facts=["medicine_name", "amount", "time_given"],
            scenario_type="unsafe_medicine",
            rationale="Human medicines and painkillers can be dangerous for dogs.",
            intent="medicine_question",
        )

    if _contains_any(screen_text, ["kerosene", "engine oil", "turpentine", "acid", "chili", "turmeric"]) and _contains_any(
        screen_text, ["wound", "maggot", "skin", "apply", "put", "use"]
    ):
        return TriageResult(
            urgency_tier="moderate",
            info_sufficient=True,
            missing_facts=["what_was_applied", "skin_or_wound_status"],
            scenario_type="unsafe_home_remedy",
            rationale="Harsh or unproven home remedies can worsen wounds or poison the dog.",
        )

    if _contains_any(screen_text, ["well", "borewell", "pit", "shaft", "drain", "pipe", "sewer"]) and _contains_any(
        screen_text, ["fell", "fall", "fallen", "stuck", "trapped", "inside", "in a", "into"]
    ):
        return TriageResult(
            urgency_tier="life_threatening",
            info_sufficient=True,
            missing_facts=["is_dog_breathing", "approx_depth", "city_or_nearest_landmark"],
            scenario_type="fall_entrapment",
            needs_helpline_first=True,
            rationale="Entrapment in a confined vertical space needs rapid rescue help.",
        )

    if _contains_any(screen_text, ["bite", "bit", "scratch", "scratched", "saliva"]) and _contains_any(
        screen_text, ["my hand", "me", "person", "human", "skin", "blood", "broke the skin", "broken skin"]
    ):
        return TriageResult(
            urgency_tier="urgent",
            info_sufficient=True,
            missing_facts=["wound_washed", "rabies_vaccine_status", "dog_observable"],
            scenario_type="rabies_exposure",
            needs_helpline_first=False,
            rationale="A bite or scratch that breaks human skin needs rabies exposure assessment.",
        )

    if _contains_any(screen_text, ["heatstroke", "heat stroke", "overheat", "overheated"]):
        return TriageResult(
            urgency_tier="life_threatening" if _contains_any(screen_text, ["collapse", "confused", "vomit"]) else "urgent",
            info_sufficient=True,
            missing_facts=["temperature_exposure", "can_swallow"],
            scenario_type="heatstroke",
            rationale="Heat illness can deteriorate quickly.",
        )

    if _contains_any(screen_text, ["not breathing", "cannot breathe", "can't breathe", "choking", "blue gums"]):
        return TriageResult(
            urgency_tier="life_threatening",
            info_sufficient=True,
            missing_facts=["is_air_moving", "visible_object"],
            scenario_type="choking_airway",
            rationale="Airway or breathing distress can become fatal within minutes.",
        )

    if _contains_any(screen_text, ["unconscious", "unresponsive", "collapsed", "collapse", "repeated seizure"]):
        return TriageResult(
            urgency_tier="life_threatening",
            info_sufficient=True,
            missing_facts=["breathing_status", "duration"],
            scenario_type="seizure_collapse",
            rationale="Collapse or unresponsiveness is an emergency sign.",
        )

    if _contains_any(screen_text, ["heavy bleeding", "blood pouring", "non-stop bleeding", "spurting blood"]):
        return TriageResult(
            urgency_tier="life_threatening",
            info_sufficient=True,
            missing_facts=["bleeding_location"],
            scenario_type="severe_bleeding",
            rationale="Heavy bleeding needs immediate pressure and urgent help.",
        )

    if _contains_any(screen_text, [
        "hit by car", "road accident", "vehicle", "bike hit", "car hit", "hit by bike", "hit by a bike", "run over",
        "गाड़ी से टकराया", "गाड़ी ने मारा", "गाडीने मारले", "सड़क दुर्घटना", "वाहन ने मारा",
    ]):
        tier = "life_threatening" if _contains_any(screen_text, [
            "cannot stand", "can't stand", "dragging", "collapsed",
            "खड़ा नहीं", "उठ नहीं", "उभा राहू शकत नाही",
        ]) else "urgent"
        return TriageResult(
            urgency_tier=tier,
            info_sufficient=True,
            missing_facts=["can_stand", "breathing_status", "visible_bleeding"],
            scenario_type="road_trauma",
            needs_helpline_first=True,
            rationale="Road trauma can involve fractures, spinal injury, or internal injury.",
        )

    if _contains_any(screen_text, TOXIN_TERMS + ["organophosphate"]):
        if _is_hypothetical_toxin_question(screen_text):
            return TriageResult(
                urgency_tier="moderate",
                info_sufficient=True,
                missing_facts=["substance", "possible_exposure"],
                scenario_type="poisoning",
                rationale="The user is asking about a toxin hypothetically, not reporting ingestion.",
                intent="medicine_question",
            )
        return TriageResult(
            urgency_tier="urgent",
            info_sufficient=True,
            missing_facts=["substance", "time_since_exposure", "symptoms"],
            scenario_type="poisoning",
            rationale="Suspected toxin exposure needs fast identification and vet guidance.",
        )

    if _contains_any(screen_text, ["maggot", "myiasis"]):
        return TriageResult(
            urgency_tier="urgent",
            info_sufficient=True,
            missing_facts=["wound_location", "dog_is_handleable"],
            scenario_type="maggot_wound",
            rationale="Maggot wounds need prompt wound care and rescue/vet treatment.",
        )

    if _contains_any(screen_text, ["tick", "ticks", "flea", "fleas"]):
        urgent = _contains_any(screen_text, ["weak", "pale", "bleeding", "fever", "not eating"])
        return TriageResult(
            urgency_tier="urgent" if urgent else "moderate",
            info_sufficient=True,
            missing_facts=["gum_color", "fever_or_weakness"],
            scenario_type="tick_infestation",
            rationale="Ticks can cause skin irritation and serious tick-borne illness when the dog is weak.",
        )

    if _contains_any(screen_text, ["mange", "hair loss", "itchy skin", "skin disease", "crusty skin"]):
        return TriageResult(
            urgency_tier="moderate",
            info_sufficient=True,
            missing_facts=["skin_broken_or_infected", "dog_is_weak"],
            scenario_type="skin_disease",
            rationale="Skin disease is described without immediate collapse or severe wound signs.",
        )

    if _contains_any(screen_text, ["fracture", "broken leg", "limping", "can't walk", "cannot walk"]):
        return TriageResult(
            urgency_tier="urgent",
            info_sufficient=True,
            missing_facts=["can_bear_weight", "pain_level"],
            scenario_type="fracture",
            rationale="Possible fracture needs immobilization and veterinary assessment.",
        )

    if _contains_any(screen_text, ["transport", "carry", "lift", "move him", "move her", "take to vet"]):
        return TriageResult(
            urgency_tier="moderate",
            info_sufficient=True,
            missing_facts=["possible_spinal_injury", "dog_size"],
            scenario_type="injured_transport",
            rationale="Transport advice should minimize pain and spinal movement.",
        )

    if _contains_any(screen_text, ["burn", "burned", "scald", "fire", "hot water", "chemical burn"]):
        return TriageResult(
            urgency_tier="urgent",
            info_sufficient=True,
            missing_facts=["burn_location", "burn_size", "chemical_or_heat"],
            scenario_type="burn_injury",
            rationale="Burns can worsen and may need urgent pain control and wound care.",
        )

    if _contains_any(screen_text, ["eye", "eyeball", "blind", "squinting"]):
        return TriageResult(
            urgency_tier="urgent",
            info_sufficient=True,
            missing_facts=["eye_open", "discharge_or_bleeding"],
            scenario_type="eye_injury",
            rationale="Eye injuries can worsen quickly without examination.",
        )

    if _is_weak_puppy_feeding_question(screen_text):
        return TriageResult(
            urgency_tier="moderate",
            info_sufficient=True,
            missing_facts=["can_swallow", "body_warmth", "mother_seen"],
            scenario_type="feeding_weak_dog",
            rationale="A weak or newly found puppy needs cautious warming and feeding guidance.",
        )

    if _contains_any(screen_text, ["puppy", "puppies"]) and _contains_any(screen_text, ["diarrhea", "diarrhoea", "vomit", "bloody"]):
        return TriageResult(
            urgency_tier="urgent",
            info_sufficient=True,
            missing_facts=["age", "blood_in_stool", "can_drink"],
            scenario_type="puppy_gi",
            rationale="Puppies can dehydrate and crash quickly.",
        )

    if _contains_any(screen_text, [
        "vomit", "vomiting", "diarrhea", "diarrhoea", "loose motion", "bloody stool",
        "दस्त", "जुलाब", "उल्टी", "ओकारी", "अतिसार",
    ]):
        urgent = _contains_any(screen_text, ["repeated", "again and again", "blood", "bloody", "weak", "collapse", "puppy"])
        return TriageResult(
            urgency_tier="urgent" if urgent else "moderate",
            info_sufficient=True,
            missing_facts=["can_keep_water_down", "blood_present", "duration"],
            scenario_type="vomiting_diarrhea",
            rationale="Vomiting or diarrhea can become urgent if repeated, bloody, or causing weakness.",
        )

    if _contains_any(screen_text, ["aggressive", "biting", "growling", "lunging", "cornered"]):
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

    if _contains_any(screen_text, FEEDING_TERMS + ["weak street dog"]):
        return TriageResult(
            urgency_tier="low_risk"
            if not _contains_any(screen_text, ["collapse", "cannot stand", "very weak", "bahut kamzor"])
            else "moderate",
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

    if _contains_any(compact, ["sad", "quiet", "a little sad", "low energy", "less active"]) and not _contains_any(
        screen_text,
        ["collapse", "cannot stand", "can't stand", "not eating", "not drinking", "breathing", "pain", "vomit", "diarrhea", "diarrhoea"],
    ):
        return TriageResult(
            urgency_tier="low_risk",
            info_sufficient=True,
            missing_facts=["appetite", "drinking", "duration"],
            scenario_type="mild_behavior_change",
            rationale="Mild behavior change is described without red flags.",
        )

    if screen_text != compact:
        return TriageResult(
            urgency_tier="low_risk",
            info_sufficient=True,
            scenario_type="symptom_negated",
            rationale="The user negated the concerning symptom instead of reporting it as active.",
        )

    return TriageResult(
        urgency_tier="moderate",
        info_sufficient=True,
        missing_facts=["breathing_status", "can_stand", "visible_injury"],
        scenario_type="unclear",
        rationale="Some detail is present, but the exact first-aid category is unclear.",
    )


def heuristic_classify_situation(
    user_message: str,
    analysis_context: str | None = None,
    last_assistant_message: str | None = None,
) -> TriageResult:
    """Public wrapper: classify then attach mode and context_used."""
    result = _heuristic_classify_internal(user_message, analysis_context, last_assistant_message)
    result.mode = _derive_mode(result.urgency_tier, result.scenario_type)
    result.context_used = bool(analysis_context and _is_context_dependent(user_message))
    return result


async def classify_situation(
    user_message: str,
    analysis_context: str | None,
    last_assistant_message: str | None = None,
) -> TriageResult:
    """Classify a chat turn before generating a full response."""
    del last_assistant_message
    fallback = heuristic_classify_situation(user_message, analysis_context)
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
