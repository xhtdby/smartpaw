"""First aid chatbot endpoint using RAG + LLM.

POST /api/chat — conversational first aid after image analysis or direct query.
Uses a curated first aid knowledge base for retrieval-augmented generation.
"""

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


def _retrieve_relevant(query: str, top_k: int = 3) -> tuple[str, list[str]]:
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
    for _, article in top:
        context_parts.append(f"**{article['title']}**\n{article['content']}")
        sources.append(article["title"])
    return "\n\n---\n\n".join(context_parts), sources


# ---------------------------------------------------------------------------
# Emergency contacts for major Indian cities — embedded in system prompt
# ---------------------------------------------------------------------------
_INDIA_EMERGENCY_CONTACTS = """
VERIFIED INDIA ANIMAL RESCUE CONTACTS (use when user asks who to call):
- Mumbai: BSPCA +91-85916-59398 (24x7 hospital)
- Delhi NCR: Friendicoes SECA +91-88829-31057 (9am–9pm; night service suspended)
- Delhi guidance: Jaagruti WhatsApp +91-98181-44244 (advice only, not ambulance)
- Bengaluru: CUPA +91-98454-25678 (9am–5pm daily, trauma & rescue)
- Hyderabad: PFA Hyderabad +91-73374-50643 (24 hours)
- Pune: RESQ Charitable Trust +91-98909-99111 (11am–5pm; 24x7 for wildlife/large animals)
- Jaipur: Help in Suffering +91-81072-99711
- Kolkata: Love N Care For Animals +91-98300-37693
- Udaipur: Animal Aid Unlimited +91-98298-43726 (stay with animal)
- Chennai: Blue Cross rescue form online (bluecrossofindia.org); ABC helpline 1913
- All India: AWBI 0129-2555700 (Mon–Fri 9am–5:30pm)
- All India emergencies (human safety): 112
"""

SYSTEM_PROMPT = """You are IndieAid, an AI first-aid assistant for dogs. Your role is to help a rescuer take the right action in the next few minutes.

PRIME DIRECTIVE — LEAD WITH IMMEDIATE ACTION:
When someone reports an injured or sick dog, your FIRST output must be the immediate first aid steps they can take RIGHT NOW. Do not open with disclaimers, "do not approach", or preamble. Start with what to DO. Safety warnings go inside the steps where they belong, not before them.

Only exceptions: if the dog is described as actively biting, lunging, cornering people, or the scene itself is dangerous (live traffic, fire, electrocution), open with a one-sentence safety note, then immediately give steps.

Response structure (always follow this):
1. **Immediate steps** — numbered, concrete, do-now actions (2–5 steps max, each ≤20 words)
2. **When to escalate** — 1–2 lines: what signs mean the dog needs a vet urgently
3. **Who to call** — if professional help is needed, give the specific city contact from the list below, not a generic "find a vet"
4. **Watch for** — what to monitor after the immediate steps (optional, 1–2 lines)

Approach safety rules (embed in steps, not as the opener):
- Move slowly, turn sideways, avoid leaning over the dog.
- Give the dog an exit route — do not corner it.
- Even friendly dogs bite when in pain. Keep face away from the mouth.
- If the dog is actively attacking or cannot be approached safely, call rescue and wait nearby.

Clinical safety rules:
- Do not recommend prescription drugs, injections, antibiotics, steroids, painkillers, dewormers, or human medicines.
- Safe first aid you may recommend: shade, water (if dog can swallow), direct pressure on bleeding, saline rinse, diluted povidone-iodine on surface wounds, clean cloth or gauze, warmth for puppies, quiet isolation.
- Explicitly warn against: kerosene, turpentine, engine oil, acid, chili, random OTC human medicines.
- You are NOT a veterinarian and must not present advice as a diagnosis.

Escalate as EMERGENCY for:
- Trouble breathing, collapse, repeated seizures, heavy or non-stop bleeding, possible spinal or internal injury, suspected poisoning, heatstroke that is not improving, bloated abdomen with retching, maggot wounds, deep bite or puncture wounds, a puppy with bloody diarrhoea, or any bite/scratch that may expose a person to rabies.

{emergency_contacts}

Resource rule: When the user needs real-world help, give the specific city contact above if they mention or imply a city. If city is unknown, direct them to Find Help in the app or to the AWBI directory.

{language_instruction}

KNOWLEDGE BASE CONTEXT:
{context}"""

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
# Action card detection — server-side, keyword-based (no LLM involvement)
# ---------------------------------------------------------------------------

_GUIDE_KEYWORDS: dict[str, list[str]] = {
    "trauma": ["bleed", "wound", "fracture", "accident", "road", "trauma", "bite", "puncture", "cut", "injur", "hit by", "crush"],
    "skin": ["mange", "maggot", "tick", "skin", "itch", "hair loss", "scab", "myiasis", "fur", "patch"],
    "heat": ["heatstroke", "heat stroke", "dehydrat", "pant", "overheat", "cool", "hot weather", "sun"],
    "poison": ["poison", "toxic", "ingest", "swallow", "xylitol", "chocolate", "pesticide", "rat poison", "chemical"],
    "puppies": ["puppy", "puppies", "newborn", "diarrh", "vomit", "parvo", "litter", "orphan", "neonatal"],
    "approach": ["aggress", "growl", "fearful", "biting", "approach", "bite risk", "scared", "attack"],
}

_EMERGENCY_KEYWORDS = [
    "urgent", "emergency", "immediately", "rush", "cannot breathe", "not breathing",
    "collapsed", "collapse", "seizure", "heavy bleeding", "poison", "unconscious",
    "unresponsive", "critical", "life-threatening", "call vet", "vet urgently",
    "veterinary care urgently", "escalate", "112", "ambulance",
]

_FIND_HELP_KEYWORDS = [
    "veterinarian", "vet", "rescue", "call", "help", "hospital", "professional",
    "contact", "clinic", "ngo", "organization",
]

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


def _build_action_cards(query: str, response: str, language: str) -> tuple[list[dict[str, Any]], bool]:
    lang = language if language in ("en", "hi", "mr") else "en"
    combined = (query + " " + response).lower()

    is_emergency = any(kw in combined for kw in _EMERGENCY_KEYWORDS)

    matched_guides: list[str] = []
    for guide_id, keywords in _GUIDE_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            matched_guides.append(guide_id)
    matched_guides = matched_guides[:2]  # at most 2 learn cards

    needs_find_help = is_emergency or any(kw in combined for kw in _FIND_HELP_KEYWORDS)

    cards: list[dict[str, Any]] = []

    if is_emergency:
        cards.append({
            "type": "emergency",
            "label": _EMERGENCY_LABEL[lang],
            "href": "/nearby",
        })

    for guide_id in matched_guides:
        cards.append({
            "type": "learn",
            "label": _GUIDE_LABELS[guide_id][lang],
            "href": f"/learn#{guide_id}",
            "guide_id": guide_id,
        })

    if needs_find_help:
        cards.append({
            "type": "find_help",
            "label": _FIND_HELP_LABEL[lang],
            "href": "/nearby",
        })

    return cards, is_emergency


@router.post("/chat")
async def chat(request: ChatRequest):
    """Chat with IndieAid about dog first aid and care."""
    settings = get_settings()

    context, sources = _retrieve_relevant(request.message)
    if request.context_from_analysis:
        context = f"Previous analysis of the dog:\n{request.context_from_analysis}\n\n---\n\n{context}"

    lang_instruction = LANGUAGE_INSTRUCTIONS.get(request.language, LANGUAGE_INSTRUCTIONS["en"])
    system = SYSTEM_PROMPT.format(
        language_instruction=lang_instruction,
        context=context,
        emergency_contacts=_INDIA_EMERGENCY_CONTACTS,
    )

    reminder = LANGUAGE_REMINDERS.get(request.language, "")
    messages = [{"role": "system", "content": system}]
    for msg in request.history[-10:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message + reminder})

    if not settings.groq_api_key:
        fallback = _fallback_chat(request.message, context, request.language)
        cards, is_emergency = _build_action_cards(request.message, fallback, request.language)
        return {"response": fallback, "sources": sources, "action_cards": cards, "is_emergency": is_emergency}

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
                    "temperature": 0.35,
                    "max_tokens": 700,
                },
            )
            response.raise_for_status()
            data = response.json()
            reply = data["choices"][0]["message"]["content"]
            cards, is_emergency = _build_action_cards(request.message, reply, request.language)
            return {"response": reply, "sources": sources, "action_cards": cards, "is_emergency": is_emergency}
    except Exception as exc:
        logger.error("Chat failed: %s", exc)
        fallback = _fallback_chat(request.message, context, request.language)
        cards, is_emergency = _build_action_cards(request.message, fallback, request.language)
        return {"response": fallback, "sources": sources, "action_cards": cards, "is_emergency": is_emergency}


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


def _fallback_chat(message: str, context: str, language: str = "en") -> str:
    del message
    lang = language if language in ("en", "hi", "mr") else "en"
    if context and "No specific first aid articles" not in context:
        return _FALLBACK_WITH_KB[lang].format(context=context)
    return _FALLBACK_GENERIC[lang]
