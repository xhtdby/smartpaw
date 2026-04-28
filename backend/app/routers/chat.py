"""First aid chatbot endpoint using RAG + LLM.

POST /api/chat — conversational first aid after image analysis or direct query.
Uses a curated first aid knowledge base for retrieval-augmented generation.
"""

import asyncio
import json
import logging
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter

from app.config import get_settings
from app.models.schemas import ChatRequest
from app.services.triage import TriageResult, classify_situation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

_knowledge_base: list[dict] = []
_idf_cache: dict[str, float] = {}
_KB_FILE = Path(__file__).parent.parent.parent / "data" / "first_aid_kb.json"

_STOP_WORDS = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would shall should may might can could to of in for on with "
    "at by from it its this that these those i me my we our you your "
    "he she they them their what which who whom how and or but not no".split()
)


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z]+", text.lower())
    return [word for word in words if word not in _STOP_WORDS and len(word) > 1]


def _load_kb() -> None:
    global _knowledge_base, _idf_cache
    if not _knowledge_base and _KB_FILE.exists():
        with open(_KB_FILE, encoding="utf-8") as file:
            _knowledge_base = json.load(file)
        logger.info("Loaded %s first aid articles.", len(_knowledge_base))

        n_docs = len(_knowledge_base)
        doc_freq: Counter = Counter()
        for article in _knowledge_base:
            text = article.get("title", "") + " " + article.get("content", "")
            tags = " ".join(article.get("tags", []))
            tokens = set(_tokenize(text + " " + tags))
            for token in tokens:
                doc_freq[token] += 1

        _idf_cache = {
            word: math.log((n_docs + 1) / (freq + 1)) + 1
            for word, freq in doc_freq.items()
        }


def _clip_text(text: str, max_chars: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "..."


def _retrieve_relevant(query: str, top_k: int = 2, max_chars: int = 600) -> tuple[str, list[str]]:
    _load_kb()
    query_tokens = _tokenize(query)
    if not query_tokens:
        return "No specific first aid articles found for this query.", []

    query_tf = Counter(query_tokens)
    scored: list[tuple[float, dict]] = []

    for article in _knowledge_base:
        text = article.get("title", "") + " " + article.get("content", "")
        tags = article.get("tags", [])

        doc_tokens = _tokenize(text)
        doc_tf = Counter(doc_tokens)
        score = 0.0
        for word, q_count in query_tf.items():
            if word in doc_tf:
                tf = 1 + math.log(doc_tf[word]) if doc_tf[word] > 0 else 0
                idf = _idf_cache.get(word, 1.0)
                score += q_count * tf * idf

        for tag in tags:
            tag_lower = tag.lower()
            for query_token in query_tokens:
                if query_token in tag_lower:
                    score += 5.0

        if score > 0:
            scored.append((score, article))

    scored.sort(key=lambda item: item[0], reverse=True)
    top = scored[:top_k]
    if not top:
        return "No specific first aid articles found for this query.", []

    context_parts: list[str] = []
    sources: list[str] = []
    remaining = max_chars
    for _, article in top:
        title = str(article["title"])
        body_budget = max(120, remaining - len(title) - 8)
        part = f"**{title}**\n{_clip_text(str(article['content']), body_budget)}"
        context_parts.append(part)
        sources.append(article["title"])
        remaining -= len(part) + 8
        if remaining <= 80:
            break
    return "\n\n---\n\n".join(context_parts), sources


# ---------------------------------------------------------------------------
# Emergency contacts for major Indian cities. Only the matching city is injected.
# ---------------------------------------------------------------------------
_CITY_EMERGENCY_CONTACTS: dict[str, str] = {
    "mumbai": "Mumbai: BSPCA +91-85916-59398 (24x7 hospital)",
    "delhi": "Delhi NCR: Friendicoes SECA +91-88829-31057 (9am-9pm; night service suspended). Jaagruti WhatsApp +91-98181-44244 for advice.",
    "ncr": "Delhi NCR: Friendicoes SECA +91-88829-31057 (9am-9pm; night service suspended). Jaagruti WhatsApp +91-98181-44244 for advice.",
    "bengaluru": "Bengaluru: CUPA +91-98454-25678 (9am-5pm daily, trauma and rescue)",
    "bangalore": "Bengaluru: CUPA +91-98454-25678 (9am-5pm daily, trauma and rescue)",
    "hyderabad": "Hyderabad: PFA Hyderabad +91-73374-50643 (24 hours)",
    "pune": "Pune: RESQ Charitable Trust +91-98909-99111 (11am-5pm; technical rescues depending on case)",
    "jaipur": "Jaipur: Help in Suffering +91-81072-99711",
    "kolkata": "Kolkata: Love N Care For Animals +91-98300-37693",
    "udaipur": "Udaipur: Animal Aid Unlimited +91-98298-43726 (stay with the animal if safe)",
    "chennai": "Chennai: Blue Cross rescue form at bluecrossofindia.org; ABC helpline 1913",
}

DEFAULT_CONTACT_LINE = (
    "If no city contact is known, open Find Help in the app or call a nearby "
    "emergency veterinarian/rescue service. For unsafe human situations in India, call 112."
)

_PROMPT_EMERGENCY = """You are IndieAid responding to an urgent dog emergency. Be concise and action-first.

Rules:
- If a helpline call is needed first, give the contact number FIRST, then 1-3 numbered steps
- Otherwise: give 1-3 numbered immediate actions — no greeting, no preamble, no disclaimer opener
- Safe first aid only: shade, water only if swallowing, direct pressure, saline rinse, careful transport
- NEVER recommend prescription drugs, injections, antibiotics, steroids, painkillers, kerosene, turpentine, engine oil, acid, or chili
- No "watch for" section — this is urgent action time
- Under 350 tokens

CONTACT:
{emergency_contact}

TRIAGE:
{triage}

{language_instruction}"""

_PROMPT_CARE = """You are IndieAid, a dog-care assistant helping with a mild symptom or care question.

This is NOT an emergency. Keep your response proportionate.

Guidance:
- Describe what you observe and the most likely possibilities without claiming certainty
- Clearly separate: what to watch at home, when to call a vet, and what would be an emergency signal
- If you need 1-2 more details for better advice, ask those specific questions — not a long checklist
- Safe first aid only: shade, water if alert, gentle observation, saline rinse, clean cloth
- Never recommend prescription drugs, antibiotics, steroids, human medicines, or unproven remedies
- Under 500 tokens

TRIAGE:
{triage}

KNOWLEDGE BASE:
{context}

{language_instruction}"""

_PROMPT_WARM = """You are IndieAid, a warm and curious dog-care assistant.

The user is greeting you, introducing their dog, or asking a general question with no urgent symptom.

Respond in 2-4 friendly sentences:
- Be genuinely warm and curious about their dog
- You may ask about the dog's name, age, breed, or what they are curious about
- You may invite care, feeding, grooming, training, or breed questions
- Do NOT open with "Of course!" or "I'm here to help!"
- Do NOT add disclaimers, checklists, or warnings unless the user describes a symptom

{language_instruction}"""

_PROMPT_REPAIR = """You are IndieAid. The user is correcting or redirecting the conversation, not reporting a new emergency.

Your response:
- Acknowledge the correction in one short sentence — do not over-apologize
- Do NOT repeat any emergency steps, warnings, or the previous topic
- Ask one open question: what they would like to focus on now
- Keep it to 2-3 sentences total

{language_instruction}"""

LANGUAGE_INSTRUCTIONS = {
    "en": "LANGUAGE: Respond in English.",
    "hi": (
        "LANGUAGE: Respond ENTIRELY in Hindi using Devanagari script. "
        "Do NOT use Roman transliteration. Medicine brand names may stay in English. "
        "Phone numbers and emergency contact names must stay in their original form."
    ),
    "mr": (
        "LANGUAGE: Respond ENTIRELY in Marathi using Devanagari script. "
        "Do NOT use Roman transliteration. Use natural Marathi, not Hindi substitutes. "
        "Phone numbers and emergency contact names must stay in their original form."
    ),
}

LANGUAGE_REMINDERS = {
    "en": "",
    "hi": "\n\nकृपया हिंदी में उत्तर दें।",
    "mr": "\n\nकृपया मराठीत उत्तर द्या.",
}

# ---------------------------------------------------------------------------
# Action cards are route-based. Do not infer scenarios from generated text.
# ---------------------------------------------------------------------------

_GUIDE_LABELS: dict[str, dict[str, str]] = {
    "approach": {"en": "Learn: Approach Safely", "hi": "जानें: सुरक्षित पास जाएँ", "mr": "शिका: सुरक्षितपणे जवळ जा"},
    "trauma": {"en": "Learn: Bleeding & Trauma", "hi": "जानें: घाव और दुर्घटना", "mr": "शिका: रक्तस्त्राव व आघात"},
    "heat": {"en": "Learn: Heatstroke & Dehydration", "hi": "जानें: हीटस्ट्रोक", "mr": "शिका: उष्माघात"},
    "poison": {"en": "Learn: Poisoning", "hi": "जानें: ज़हर", "mr": "शिका: विषबाधा"},
    "skin": {"en": "Learn: Maggots & Skin Disease", "hi": "जानें: कीड़े और त्वचा", "mr": "शिका: अळ्या व त्वचारोग"},
    "puppies": {"en": "Learn: Puppies & Diarrhoea", "hi": "जानें: पिल्ले और दस्त", "mr": "शिका: पिल्ले व जुलाब"},
}

_FIND_HELP_LABEL: dict[str, str] = {
    "en": "Find Help Near You",
    "hi": "पास में मदद खोजें",
    "mr": "जवळची मदत शोधा",
}

_EMERGENCY_LABEL: dict[str, str] = {
    "en": "Emergency — Call Now",
    "hi": "आपातकाल — अभी कॉल करें",
    "mr": "आपत्कालीन — आत्ता कॉल करा",
}


def _build_triage_action_cards(
    query: str,
    response: str,
    language: str,
    triage: TriageResult,
) -> tuple[list[dict[str, Any]], bool]:
    del query, response
    if not triage.info_sufficient:
        return [], False

    lang = language if language in ("en", "hi", "mr") else "en"
    scenario = triage.scenario_type

    quiet_scenarios = {
        "conversation_repair",
        "warm_conversation",
        "symptom_negated",
        "healthy_or_low_risk",
        "mild_behavior_change",
        "no_dog_visible",
        "deceased_pet",
    }
    if scenario in quiet_scenarios:
        return [], False

    emergency_scenarios = {
        "fall_entrapment",
        "choking_airway",
        "seizure_collapse",
        "severe_bleeding",
        "heatstroke",
        "road_trauma",
        "poisoning",
        "rabies_exposure",
    }
    guide_by_scenario = {
        "severe_bleeding": "trauma",
        "road_trauma": "trauma",
        "fracture": "trauma",
        "injured_transport": "trauma",
        "burn_injury": "trauma",
        "maggot_wound": "skin",
        "skin_disease": "skin",
        "tick_infestation": "skin",
        "heatstroke": "heat",
        "poisoning": "poison",
        "unsafe_medicine": "poison",
        "puppy_gi": "puppies",
        "vomiting_diarrhea": "puppies",
        "fearful_aggressive": "approach",
        "fall_entrapment": "approach",
    }

    is_emergency = scenario in emergency_scenarios and triage.urgency_tier in {"life_threatening", "urgent"}
    cards: list[dict[str, Any]] = []

    if is_emergency:
        cards.append({"type": "emergency", "label": _EMERGENCY_LABEL[lang], "href": "/nearby"})

    guide_id = guide_by_scenario.get(scenario)
    if guide_id:
        cards.append({
            "type": "learn",
            "label": _GUIDE_LABELS[guide_id][lang],
            "href": f"/learn#{guide_id}",
            "guide_id": guide_id,
        })

    needs_find_help = is_emergency or (
        triage.urgency_tier == "urgent"
        and scenario not in {"routine_care", "feeding_weak_dog", "lost_dog"}
    )
    if needs_find_help:
        cards.append({"type": "find_help", "label": _FIND_HELP_LABEL[lang], "href": "/nearby"})

    return cards, is_emergency


def _matching_emergency_contact(text: str) -> str:
    haystack = text.lower()
    for city, contact in _CITY_EMERGENCY_CONTACTS.items():
        if re.search(rf"\b{re.escape(city)}\b", haystack):
            return contact
    return DEFAULT_CONTACT_LINE


def _history_for_model(history: list[Any]) -> list[dict[str, str]]:
    """Keep recent turns verbatim and compress older turns into one short block."""
    if len(history) <= 6:
        return [{"role": msg.role, "content": msg.content} for msg in history]

    older = history[:-4]
    recent = history[-4:]
    snippets: list[str] = []
    for msg in older[-8:]:
        content = _clip_text(getattr(msg, "content", ""), 180)
        if content:
            snippets.append(f"{getattr(msg, 'role', 'user')}: {content}")
    summary = _clip_text("Situation so far: " + " | ".join(snippets), 900)
    return [{"role": "assistant", "content": summary}] + [
        {"role": msg.role, "content": msg.content} for msg in recent
    ]


def _build_clarifying_reply(triage: TriageResult, language: str) -> str:
    questions_by_fact = {
        "main_symptom": "What is the main thing you are seeing right now: breathing problem, bleeding, vomiting/diarrhea, collapse, pain, or behavior change?",
        "breathing_and_responsiveness": "Is the dog breathing normally and responding to voice or touch?",
        "recent_event_or_exposure": "Did anything happen recently: fall, accident, heat exposure, poison/chemical, bite, or unknown?",
        "what_happened": "What happened just before you messaged?",
        "current_symptoms": "What symptoms can you see right now?",
        "visible_injury": "Do you see bleeding, swelling, a wound, or a limb held oddly?",
        "can_stand": "Can the dog stand or walk at all?",
        "breathing_status": "Is breathing normal, noisy, very fast, or absent?",
    }
    selected: list[str] = []
    for fact in triage.missing_facts:
        question = questions_by_fact.get(fact)
        if question and question not in selected:
            selected.append(question)
        if len(selected) == 2:
            break
    if not selected:
        selected = [
            "Is the dog breathing normally and responding?",
            "What exactly happened or changed just before this?",
        ]

    if language == "hi":
        return "पहले ये दो बातें बताएं:\n1. क्या कुत्ता सामान्य सांस ले रहा है और आवाज/छूने पर प्रतिक्रिया दे रहा है?\n2. अभी मुख्य समस्या क्या दिख रही है?"
    if language == "mr":
        return "आधी या दोन गोष्टी सांगा:\n1. कुत्रा नीट श्वास घेतोय आणि आवाज/स्पर्शाला प्रतिसाद देतोय का?\n2. आत्ता मुख्य त्रास काय दिसतोय?"
    return "Two things first:\n" + "\n".join(f"{idx}. {question}" for idx, question in enumerate(selected, 1))


def _triage_dict(triage: TriageResult) -> dict[str, Any]:
    return triage.model_dump()


_WARM_FALLBACK: dict[str, str] = {
    "en": (
        "Hi! I'm here. Tell me about your dog — name, age, indie mix or known breed, "
        "or whatever you're curious about."
    ),
    "hi": (
        "नमस्ते! बताइए — कुत्ते का नाम, उम्र, नस्ल क्या है, "
        "या आप किस बारे में जानना चाहते हैं?"
    ),
    "mr": (
        "नमस्कार! सांगा — कुत्र्याचे नाव, वय, जात काय आहे, "
        "किंवा तुम्हाला कशाबद्दल जाणायचे आहे?"
    ),
}

_REPAIR_FALLBACK: dict[str, str] = {
    "en": "Got it — I'll set that aside. What would you like to focus on right now?",
    "hi": "ठीक है — मैं उसे छोड़ता हूँ। अभी आप किस बारे में बात करना चाहते हैं?",
    "mr": "समजले — ते सोडतो. आत्ता तुम्हाला कशाबद्दल बोलायचे आहे?",
}

_SYMPTOM_NEGATED_FALLBACK: dict[str, str] = {
    "en": (
        "Got it — I won't treat that as active. "
        "What are you seeing right now? If breathing is normal, the dog can stand, "
        "and there's no heavy bleeding, collapse, or pain, we can take this step by step."
    ),
    "hi": (
        "ठीक है — वह लक्षण सक्रिय नहीं है। अभी क्या दिख रहा है? "
        "अगर सांस सामान्य है, कुत्ता खड़ा हो सकता है, "
        "और कोई गंभीर रक्तस्त्राव, बेहोशी, या दर्द नहीं है, "
        "तो हम मिलकर धीरे-धीरे आगे बढ़ते हैं।"
    ),
    "mr": (
        "ठीक आहे — तो लक्षण सक्रिय नाही. आत्ता काय दिसतंय? "
        "श्वास सामान्य असेल, कुत्रा उभा राहू शकत असेल, "
        "आणि जोरदार रक्तस्त्राव, कोसळणे, किंवा वेदना नसेल "
        "तर आपण टप्प्याटप्प्याने बघू."
    ),
}

_DECEASED_FALLBACK: dict[str, str] = {
    "en": (
        "I'm sorry. If she has already passed, this does not need an emergency checklist. "
        "If you are not completely sure she has passed, call a vet or rescue now; otherwise I can help with aftercare, what to do next, or just hear about her."
    ),
    "hi": (
        "मुझे दुख है। अगर वह अब नहीं रही, तो इसे आपातकालीन चेकलिस्ट की तरह नहीं लेना है। "
        "अगर आपको पूरी तरह यकीन नहीं है, तो अभी पशु-चिकित्सक या रेस्क्यू से बात करें; वरना मैं आगे क्या करना है या उसकी यादों के बारे में सुन सकता हूँ।"
    ),
    "mr": (
        "मला वाईट वाटते। ती आता नसल्याची खात्री असेल, तर हे आपत्कालीन चेकलिस्टसारखे हाताळायचे नाही। "
        "पूर्ण खात्री नसेल तर आत्ताच पशुवैद्य किंवा रेस्क्यूशी बोला; नाहीतर पुढे काय करायचे किंवा तिच्या आठवणींबद्दल मी ऐकू शकतो."
    ),
}


def _build_system_prompt(
    triage: TriageResult,
    lang_instruction: str,
    context: str,
    contact: str,
) -> str:
    mode = triage.mode
    triage_json = json.dumps(_triage_dict(triage), ensure_ascii=False)
    if mode == "emergency":
        return _PROMPT_EMERGENCY.format(
            language_instruction=lang_instruction,
            emergency_contact=contact,
            triage=triage_json,
        )
    if mode == "warm":
        return _PROMPT_WARM.format(language_instruction=lang_instruction)
    if mode == "repair":
        return _PROMPT_REPAIR.format(language_instruction=lang_instruction)
    return _PROMPT_CARE.format(
        language_instruction=lang_instruction,
        triage=triage_json,
        context=context,
    )


def _fallback_for_triage(
    message: str,
    context: str,
    triage: TriageResult,
    contact_context: str | None = None,
) -> str | None:
    contact = _matching_emergency_contact(contact_context or f"{message} {context}")
    scenario = triage.scenario_type

    if scenario == "conversation_repair":
        return (
            "You're right - I may have carried the previous topic forward. "
            "Tell me what is happening now, and I will treat it as a fresh question."
        )
    if scenario == "warm_conversation":
        return (
            "Hi, I'm here. Tell me about the dog - name, age, indie mix or known breed, "
            "or anything you are curious about. If something looks worrying, describe that too."
        )
    if scenario == "symptom_negated":
        return (
            "Got it - I will not treat that symptom as active. What are you seeing right now? "
            "If breathing is normal, the dog can stand, and there is no heavy bleeding, collapse, "
            "poison exposure, or severe pain, we can keep this in care mode."
        )
    if scenario == "mild_behavior_change":
        return (
            "That does not sound like an emergency from what you have said. Check whether the dog is "
            "eating, drinking, walking normally, breathing comfortably, and responding to you. "
            "Call a vet or rescue sooner if this is new and worsening, lasts more than a day, "
            "or comes with vomiting, diarrhea, pain, collapse, or refusal to eat."
        )

    if scenario == "fall_entrapment":
        lower_question = any(word in message.lower() for word in ["rope", "food", "water", "basket", "lower"])
        if lower_question:
            return (
                f"{contact}\n"
                "1. Do not lower yourself into the well and do not throw food or loose objects down.\n"
                "2. If rescuers ask, lower only a wide cloth/basket/loop from above; never tighten anything around the neck.\n"
                "3. Keep talking softly and keep people away from the edge until trained help arrives."
            )
        return (
            f"{contact}\n"
            "1. Call rescue/fire services now; this needs ropes or confined-space equipment.\n"
            "2. Do not climb into the well or let bystanders crowd the edge.\n"
            "3. Keep talking softly and watch breathing/movement until trained help arrives."
        )
    if scenario == "choking_airway":
        return (
            "1. If air is moving and the dog can cough, keep it calm and let it cough.\n"
            "2. If an object is visible at the front of the mouth, remove it carefully without pushing deeper.\n"
            "3. Blue gums, silent choking, or collapse means emergency transport now."
        )
    if scenario == "seizure_collapse":
        return (
            "1. Move objects away and keep the dog away from stairs, traffic, or water.\n"
            "2. Do not put hands, food, water, or medicine in the mouth.\n"
            "3. Time the seizure/collapse and arrange urgent veterinary help."
        )
    if scenario == "severe_bleeding":
        return (
            "1. Apply firm direct pressure with a clean cloth for at least 3 minutes.\n"
            "2. Add more cloth on top if it soaks through; do not peel the first layer away.\n"
            "3. Heavy or spurting bleeding needs urgent transport/rescue help."
        )
    if scenario == "heatstroke":
        return (
            "1. Move the dog to shade or a cool indoor space immediately.\n"
            "2. Cool belly, groin, armpits, paws, and neck with room-temperature water.\n"
            "3. Offer small sips only if alert and able to swallow; arrange urgent care."
        )
    if scenario in {"fracture", "road_trauma"}:
        return (
            "1. Keep the dog still and limit movement; assume pain, fracture, or internal injury.\n"
            "2. Slide onto a board, blanket, or cardboard for transport without twisting the spine.\n"
            "3. Do not straighten limbs, pull legs, or force walking."
        )
    if scenario == "injured_transport":
        return (
            "1. Prepare the vehicle first so the dog only has to be moved once.\n"
            "2. Use a blanket, board, or sturdy cardboard to support the whole body.\n"
            "3. Do not lift by legs, collar, tail, or scruff; keep the back and neck as straight as possible."
        )
    if scenario == "poisoning":
        return (
            "1. Move the dog away from the poison and keep the packet/container for the vet.\n"
            "2. Do not induce vomiting or give milk, oil, salt, or home remedies.\n"
            "3. Call an emergency veterinarian or poison service now with amount and time."
        )
    if scenario == "unsafe_medicine":
        return (
            "1. Do not give human painkillers or leftover medicines unless a veterinarian specifically tells you.\n"
            "2. If the dog already swallowed it, note the medicine name, strength, amount, and time.\n"
            "3. Call a veterinarian or poison service now if any human medicine was swallowed."
        )
    if scenario == "maggot_wound":
        return (
            "1. Keep the dog calm and protect the wound from more flies.\n"
            "2. Cover loosely with clean gauze or cloth; use saline only for gentle surface rinsing.\n"
            "3. Do not pour kerosene, engine oil, turpentine, acid, or harsh chemicals on maggots."
        )
    if scenario == "unsafe_home_remedy":
        return (
            "1. Do not use kerosene, engine oil, turpentine, acid, chili, or thick pastes on wounds or skin.\n"
            "2. If something was already applied, gently prevent licking and rinse only with clean water/saline if safe.\n"
            "3. Use a clean loose cloth for transport and arrange vet/rescue help for open, painful, or infected wounds."
        )
    if scenario == "tick_infestation":
        return (
            "1. Check gum color and energy; pale gums, fever, bleeding, or weakness needs urgent veterinary care.\n"
            "2. Remove visible ticks with tweezers, pulling straight out close to the skin.\n"
            "3. Do not pour pesticides, kerosene, engine oil, or harsh chemicals on the dog."
        )
    if scenario == "skin_disease":
        return (
            "1. Give clean water, food, and a quiet place away from flies and traffic.\n"
            "2. Do not use kerosene, engine oil, acid, chili, or random skin medicines.\n"
            "3. Arrange vet/rescue help if skin is open, foul-smelling, bleeding, or the dog is weak."
        )
    if scenario == "burn_injury":
        return (
            "1. Move the dog away from heat or chemical exposure and keep it calm.\n"
            "2. Cool the burned area with clean room-temperature running water for several minutes.\n"
            "3. Do not apply oil, butter, toothpaste, ice, or harsh antiseptics."
        )
    if scenario == "puppy_gi":
        return (
            "1. Keep the puppy warm, quiet, and away from other dogs.\n"
            "2. Offer tiny amounts of water only if alert and not vomiting repeatedly.\n"
            "3. Bloody diarrhea or weakness in a puppy needs urgent veterinary help."
        )
    if scenario == "vomiting_diarrhea":
        return (
            "1. Offer small sips of water only if the dog is alert and not vomiting continuously.\n"
            "2. Do not give human anti-diarrhea, pain, antibiotic, or nausea medicines.\n"
            "3. Blood, repeated vomiting, weakness, bloated belly, or a puppy case needs urgent veterinary care."
        )
    if scenario == "eye_injury":
        return (
            "1. Stop the dog rubbing the eye and keep it calm in shade.\n"
            "2. If available, moisten the eye area with sterile saline; do not use random drops.\n"
            "3. Swelling, bleeding, or a closed/bulging eye needs urgent veterinary care."
        )
    if scenario == "fearful_aggressive":
        return (
            "1. Create distance and ask people to step back quietly.\n"
            "2. Do not corner, grab, stare at, or punish the dog.\n"
            "3. Call experienced rescue if the dog is injured but cannot be approached safely."
        )
    if scenario == "rabies_exposure":
        return (
            "1. Wash the bite or scratch with soap and running water for 15 minutes.\n"
            "2. Go to a doctor or emergency clinic today for rabies post-exposure advice.\n"
            "3. If safe, note where the dog is; do not try to catch an aggressive dog yourself."
        )
    if scenario == "healthy_or_low_risk":
        return (
            "1. Observe from a comfortable distance for breathing, walking, appetite, and alertness.\n"
            "2. Offer clean water and shade if the dog is outdoors.\n"
            "3. Get help if vomiting, diarrhea, limping, wounds, collapse, or breathing trouble appears."
        )
    if scenario == "lost_dog":
        return (
            "1. Keep the dog in a safe, shaded area away from traffic if it is calm enough.\n"
            "2. Check for a collar tag, ask nearby guards/shops, and post a clear photo with location.\n"
            "3. If the dog is injured, aggressive, or blocking traffic, call local rescue instead of forcing contact."
        )
    if scenario == "feeding_weak_dog":
        return (
            "1. Offer clean water first, in a shallow bowl, and watch if the dog can swallow normally.\n"
            "2. Give a small amount of bland food; do not give a large meal to a very thin or weak dog.\n"
            "3. Avoid spicy food, bones, sweets, milk-heavy meals, and human medicines."
        )
    if scenario == "routine_care":
        return (
            "1. This is not an emergency if the puppy is bright, eating, and breathing normally.\n"
            "2. Book a veterinarian visit for a vaccine and deworming schedule based on age and prior records.\n"
            "3. Keep the puppy away from sick/unvaccinated dogs until the vet says protection is adequate."
        )
    if scenario == "no_dog_visible":
        return (
            "1. Retake the photo with the dog visible, well-lit, and not blocked by objects.\n"
            "2. Add a short note about what happened and any symptoms you can see.\n"
            "3. If there is an emergency off-camera, describe it in chat and call local help."
        )
    if triage.urgency_tier in {"life_threatening", "urgent"}:
        return (
            "1. Keep the dog still, calm, and away from traffic or crowds.\n"
            "2. Check breathing, bleeding, responsiveness, and whether the dog can stand.\n"
            "3. Contact local rescue or an emergency veterinarian now if any red flag is present."
        )
    return None


def _effective_context(request: ChatRequest) -> str | None:
    """Return analysis context text; structured analysis_context wins over legacy string."""
    if request.analysis_context:
        ctx = request.analysis_context
        parts: list[str] = []
        if ctx.emotion:
            parts.append(f"Emotion: {ctx.emotion.label}")
        if ctx.condition:
            c = ctx.condition
            if c.physical_condition:
                parts.append(c.physical_condition)
            if c.visible_injuries:
                parts.append(f"Injuries: {', '.join(c.visible_injuries)}")
            if c.health_concerns:
                parts.append(f"Concerns: {', '.join(c.health_concerns)}")
        if ctx.user_context:
            parts.append(f"User context: {ctx.user_context}")
        if ctx.scenario_type and ctx.scenario_type != "unclear":
            parts.append(f"Scenario: {ctx.scenario_type}")
        if ctx.urgency_signals:
            parts.append(f"Urgency signals: {', '.join(ctx.urgency_signals)}")
        if ctx.unknown_factors:
            parts.append(f"Unknown factors: {', '.join(ctx.unknown_factors)}")
        return "\n".join(parts) or None
    return request.context_from_analysis or None


@router.post("/chat")
async def chat(request: ChatRequest):
    """Chat with IndieAid about dog first aid and care."""
    settings = get_settings()
    analysis_ctx = _effective_context(request)

    triage_task = asyncio.create_task(
        classify_situation(
            request.message,
            analysis_ctx,
        )
    )

    retrieval_query = request.message
    if analysis_ctx:
        retrieval_query = f"{request.message}\n{analysis_ctx}"
    context, sources = _retrieve_relevant(retrieval_query)
    if analysis_ctx:
        context = (
            "Previous analysis of the dog:\n"
            f"{_clip_text(analysis_ctx, 800)}\n\n---\n\n{context}"
        )

    triage = await triage_task
    contact_context = " ".join(
        [request.message, analysis_ctx or ""]
        + [msg.content for msg in request.history[-6:] if getattr(msg, "role", "") == "user"]
    )

    if triage.scenario_type == "deceased_pet":
        reply = _mode_fallback(request.message, context, request.language, triage, contact_context)
        cards, is_emergency = _build_triage_action_cards(request.message, reply, request.language, triage)
        return {
            "response": reply,
            "sources": sources,
            "action_cards": cards,
            "is_emergency": is_emergency,
            "triage": _triage_dict(triage),
        }

    if not triage.info_sufficient:
        reply = _build_clarifying_reply(triage, request.language)
        cards, is_emergency = _build_triage_action_cards(request.message, reply, request.language, triage)
        return {
            "response": reply,
            "sources": sources,
            "action_cards": cards,
            "is_emergency": is_emergency,
            "triage": _triage_dict(triage),
        }

    if not settings.groq_api_key:
        fallback = _mode_fallback(request.message, context, request.language, triage, contact_context)
        cards, is_emergency = _build_triage_action_cards(request.message, fallback, request.language, triage)
        return {
            "response": fallback,
            "sources": sources,
            "action_cards": cards,
            "is_emergency": is_emergency,
            "triage": _triage_dict(triage),
        }

    lang_instruction = LANGUAGE_INSTRUCTIONS.get(request.language, LANGUAGE_INSTRUCTIONS["en"])
    contact = _matching_emergency_contact(contact_context)
    system = _build_system_prompt(triage, lang_instruction, context, contact)

    reminder = LANGUAGE_REMINDERS.get(request.language, "")
    messages = [{"role": "system", "content": system}]
    messages.extend(_history_for_model(request.history))
    messages.append({"role": "user", "content": request.message + reminder})

    mode = triage.mode
    temperature = 0.2 if mode == "emergency" else 0.5 if mode == "warm" else 0.35
    max_tokens = 350 if mode == "emergency" else 250 if mode in ("warm", "repair") else 550

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.groq_text_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            reply = data["choices"][0]["message"]["content"]
            cards, is_emergency = _build_triage_action_cards(request.message, reply, request.language, triage)
            return {
                "response": reply,
                "sources": sources,
                "action_cards": cards,
                "is_emergency": is_emergency,
                "triage": _triage_dict(triage),
            }
    except Exception as exc:
        logger.error("Chat failed: %s", exc)
        fallback = _mode_fallback(request.message, context, request.language, triage, contact_context)
        cards, is_emergency = _build_triage_action_cards(request.message, fallback, request.language, triage)
        return {
            "response": fallback,
            "sources": sources,
            "action_cards": cards,
            "is_emergency": is_emergency,
            "triage": _triage_dict(triage),
        }


_FALLBACK_WITH_KB = {
    "en": (
        "I could not reach the AI model right now. Here is grounded guidance from the built-in first aid knowledge base:\n\n"
        "{context}\n\n"
        "If the dog shows emergency signs, contact a local rescue service immediately."
    ),
    "hi": (
        "अभी AI मॉडल तक नहीं पहुँच पा रहा। नीचे अंतर्निहित प्राथमिक-चिकित्सा ज्ञानकोश का मार्गदर्शन है:\n\n"
        "{context}\n\n"
        "अगर कुत्ते में आपातकालीन लक्षण हैं, तुरंत स्थानीय बचाव सेवा से संपर्क करें।"
    ),
    "mr": (
        "आत्ता AI मॉडेलपर्यंत पोहोचू शकलो नाही. खाली अंगभूत प्रथमोपचार ज्ञानसाठ्यातील मार्गदर्शन आहे:\n\n"
        "{context}\n\n"
        "कुत्र्यात आपत्कालीन लक्षणे दिसत असतील तर त्वरित स्थानिक बचाव सेवेशी संपर्क करा."
    ),
}

_FALLBACK_GENERIC = {
    "en": (
        "I'm having trouble connecting right now. Use these safe basics while you sort it out:\n\n"
        "**If the dog is injured:**\n"
        "1. Check for traffic or other hazards — move the dog to safety if you can do it without harming it further.\n"
        "2. If it is bleeding, apply firm, direct pressure with a clean cloth and hold for 3+ minutes.\n"
        "3. Keep the dog warm and still. Do not try to straighten limbs or remove embedded objects.\n"
        "4. Offer water only if the dog is alert and can swallow.\n\n"
        "**Get emergency help if you see:** trouble breathing, collapse, seizures, heavy bleeding, "
        "suspected poisoning, heatstroke, bloated belly, or a bite that may expose a person to rabies.\n\n"
        "Open **Find Help** in the app for verified local contacts."
    ),
    "hi": (
        "अभी कनेक्ट करने में दिक्कत है। फिलहाल ये सुरक्षित बुनियादी कदम अपनाएँ:\n\n"
        "**अगर कुत्ता घायल है:**\n"
        "1. पहले ट्रैफिक या अन्य खतरे जाँचें — अगर बिना और चोट पहुँचाए संभव हो तो कुत्ते को सुरक्षित स्थान पर लाएँ।\n"
        "2. खून बह रहा हो तो साफ कपड़े से सीधा और मजबूत दबाव दें, कम से कम 3 मिनट तक रखें।\n"
        "3. कुत्ते को गर्म और स्थिर रखें। हड्डी सीधी करने या धँसी वस्तु निकालने की कोशिश न करें।\n"
        "4. पानी तभी दें जब कुत्ता होश में हो और निगल पा रहा हो।\n\n"
        "**इन संकेतों पर तुरंत मदद लें:** साँस की दिक्कत, बेहोशी, दौरे, बहुत खून, ज़हर की आशंका, हीटस्ट्रोक।\n\n"
        "ऐप में **Find Help** खोलें — वहाँ सत्यापित स्थानीय संपर्क हैं।"
    ),
    "mr": (
        "आत्ता कनेक्ट होण्यात अडचण आहे. तोपर्यंत हे सुरक्षित मूलभूत टप्पे वापरा:\n\n"
        "**कुत्रा जखमी असल्यास:**\n"
        "1. आधी वाहतूक किंवा इतर धोके तपासा — आणखी दुखापत न होता शक्य असेल तर कुत्र्याला सुरक्षित जागी न्या.\n"
        "2. रक्तस्त्राव होत असेल तर स्वच्छ कापडाने थेट व घट्ट दाब द्या, किमान ३ मिनिटे ठेवा.\n"
        "3. कुत्र्याला उबदार व स्थिर ठेवा. हाडे सरळ करण्याचा किंवा घुसलेली वस्तू काढण्याचा प्रयत्न करू नका.\n"
        "4. कुत्रा सावध असेल आणि गिळू शकत असेल तरच पाणी द्या.\n\n"
        "**या लक्षणांवर तातडीने मदत घ्या:** श्वासाचा त्रास, कोसळणे, झटके, जोरदार रक्तस्त्राव, विषबाधा, उष्माघात.\n\n"
        "अ‍ॅपमध्ये **Find Help** उघडा — तिथे पडताळलेले स्थानिक संपर्क आहेत."
    ),
}


def _mode_fallback(
    message: str,
    context: str,
    language: str,
    triage: TriageResult,
    contact_context: str | None = None,
) -> str:
    """Return a mode-appropriate deterministic reply when the LLM is unavailable."""
    lang = language if language in ("en", "hi", "mr") else "en"
    mode = triage.mode
    scenario = triage.scenario_type

    if scenario == "deceased_pet":
        return _DECEASED_FALLBACK[lang]

    if mode == "warm":
        return _WARM_FALLBACK[lang]

    if mode == "repair" or scenario == "conversation_repair":
        return _REPAIR_FALLBACK[lang]

    if scenario == "symptom_negated":
        return _SYMPTOM_NEGATED_FALLBACK[lang]

    if lang == "en":
        scenario_reply = _fallback_for_triage(message, context, triage, contact_context)
        if scenario_reply:
            return scenario_reply

    if context and "No specific first aid articles" not in context:
        return _FALLBACK_WITH_KB[lang].format(context=context)
    return _FALLBACK_GENERIC[lang]
