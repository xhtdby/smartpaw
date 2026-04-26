"""First aid chatbot endpoint using RAG + LLM.

POST /api/chat - conversational follow-up after image analysis.
Uses a curated first aid knowledge base for retrieval-augmented generation.
"""

import json
import logging
import math
import re
from collections import Counter
from pathlib import Path

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
    """Lowercase tokenization with stop-word removal."""
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
    """TF-IDF-inspired retrieval with tag boosting from the knowledge base."""
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


SYSTEM_PROMPT = """You are IndieAid, an AI assistant helping people care for dogs with grounded first-aid guidance.

Your job is to help a rescuer make the next safe decision. Be decisive when the evidence is strong. When it is not strong, explain the main possibilities, how to tell them apart, and the safest next step for each.

Core rules:
- You are NOT a veterinarian and must not present your advice as a diagnosis.
- ALWAYS follow the language instruction below. It overrides previous messages.
- Use the knowledge-base context below as your primary factual anchor.
- Be calm, direct, practical, and compassionate.

Clinical safety rules:
- Prioritize human safety first. If the dog is aggressive, convulsing, trapped in traffic, or there is a bite or rabies risk to a person, say so immediately.
- If the condition looks clear from the user's description, say the likely problem plainly and give useful first-aid steps.
- If the condition is unclear, give the most likely possibilities, what to check next, and what action is safe across those possibilities.
- Do not recommend prescription treatment plans, injections, antibiotics, steroids, painkillers, dewormers, anti-diarrhoeals, or human medicines unless the user is explicitly relaying a veterinarian's existing prescription.
- Do not invent medicine doses.
- Low-risk first aid you may recommend includes: moving to shade, offering water if safe, direct pressure for bleeding, saline rinsing, diluted povidone-iodine on superficial wounds, clean cloth or gauze, warmth for weak puppies, isolation from other animals, and gentle transport with minimal movement.
- Explicitly warn against unsafe remedies such as kerosene, turpentine, engine oil, acid, chili, or random over-the-counter human medicines.

Escalate urgently for:
- trouble breathing, collapse, repeated seizures, heavy bleeding, possible fracture or spinal injury, severe eye injury, suspected poisoning, heatstroke, bloated abdomen with retching, maggot wounds, deep bites or punctures, a puppy with bloody diarrhoea, or any bite or scratch that may expose a person to rabies.

Resource rules:
- Do not give outdated or unverified helpline numbers.
- When the user needs real-world help, direct them to verified local veterinary care, emergency care, or trusted resources from the knowledge base or Find Help page.
- Keep India-specific legal or rescue guidance accurate, but do not assume the user is in Mumbai unless they say so.

Response shape:
- Start with the most important safety point.
- Then give concise next steps.
- Then say when professional help is needed.
- If useful, end with what to monitor next.

{language_instruction}

KNOWLEDGE BASE CONTEXT:
{context}"""

LANGUAGE_INSTRUCTIONS = {
    "en": "LANGUAGE: Always respond in English, regardless of the language used in previous messages.",
    "hi": (
        "LANGUAGE: Always respond ENTIRELY in Hindi using Devanagari script, "
        "regardless of the language used in previous messages. "
        "Do NOT use Roman transliteration. Medicine brand names may stay in English."
    ),
    "mr": (
        "LANGUAGE: Always respond ENTIRELY in Marathi using Devanagari script, "
        "regardless of the language used in previous messages. "
        "Do NOT use Roman transliteration. Use natural Marathi, not Hindi substitutes."
    ),
}

LANGUAGE_REMINDERS = {
    "en": "",
    "hi": "\n\nकृपया हिंदी में उत्तर दें।",
    "mr": "\n\nकृपया मराठीत उत्तर द्या।",
}


@router.post("/chat")
async def chat(request: ChatRequest):
    """Chat with IndieAid about dog first aid and care."""
    settings = get_settings()

    context, sources = _retrieve_relevant(request.message)
    if request.context_from_analysis:
        context = f"Previous analysis of the dog:\n{request.context_from_analysis}\n\n---\n\n{context}"

    lang_instruction = LANGUAGE_INSTRUCTIONS.get(request.language, LANGUAGE_INSTRUCTIONS["en"])
    system = SYSTEM_PROMPT.format(language_instruction=lang_instruction, context=context)

    reminder = LANGUAGE_REMINDERS.get(request.language, "")
    messages = [{"role": "system", "content": system}]
    for msg in request.history[-10:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message + reminder})

    if not settings.groq_api_key:
        return {
            "response": _fallback_chat(request.message, context, request.language),
            "sources": sources,
        }

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
                    "temperature": 0.45,
                    "max_tokens": 800,
                },
            )
            response.raise_for_status()
            data = response.json()
            reply = data["choices"][0]["message"]["content"]
            return {"response": reply, "sources": sources}
    except Exception as exc:
        logger.error("Chat failed: %s", exc)
        return {
            "response": _fallback_chat(request.message, context, request.language),
            "sources": sources,
        }


_FALLBACK_WITH_KB = {
    "en": (
        "I could not reach the language model just now, so here is grounded guidance from the built-in first-aid knowledge base:\n\n"
        "{context}\n\n"
        "If the dog has any emergency signs, contact a local veterinarian or rescue service immediately."
    ),
    "hi": (
        "अभी मैं भाषा मॉडल तक नहीं पहुँच पा रहा हूँ, इसलिए नीचे मेरे अंतर्निहित प्राथमिक-चिकित्सा ज्ञानकोश से विश्वसनीय मार्गदर्शन दिया गया है:\n\n"
        "{context}\n\n"
        "अगर कुत्ते में कोई आपातकालीन लक्षण हैं, तो तुरंत स्थानीय पशु-चिकित्सक या बचाव सेवा से संपर्क करें।"
    ),
    "mr": (
        "आत्ता मी भाषा मॉडेलपर्यंत पोहोचू शकलो नाही, म्हणून खाली अंगभूत प्रथमोपचार ज्ञानसाठ्यातील विश्वसनीय मार्गदर्शन दिले आहे:\n\n"
        "{context}\n\n"
        "कुत्र्यात कोणतीही आपत्कालीन लक्षणे दिसत असतील, तर त्वरित स्थानिक पशुवैद्य किंवा बचाव सेवेशी संपर्क करा."
    ),
}

_FALLBACK_GENERIC = {
    "en": (
        "I am having trouble connecting right now. For the moment, use these safe basics:\n\n"
        "1. Keep yourself safe and do not corner the dog.\n"
        "2. If the dog is overheated, move it to shade and offer water if safe.\n"
        "3. If there is bleeding, use direct pressure with a clean cloth.\n"
        "4. If the dog is collapsed, struggling to breathe, badly injured, or poisoned, get emergency veterinary help immediately.\n\n"
        "If you are unsure what the problem is, check the nearest red-flag sign first: breathing, bleeding, collapse, severe pain, poisoning, or inability to stand."
    ),
    "hi": (
        "अभी कनेक्ट करने में दिक्कत हो रही है। फिलहाल ये सुरक्षित मूल कदम अपनाएँ:\n\n"
        "1. पहले अपनी सुरक्षा रखें और कुत्ते को घेरें नहीं।\n"
        "2. अगर कुत्ता गर्मी से परेशान है, तो उसे छाया में ले जाएँ और सुरक्षित हो तो पानी दें।\n"
        "3. अगर खून बह रहा है, तो साफ कपड़े से सीधा दबाव दें।\n"
        "4. अगर कुत्ता गिर गया है, साँस लेने में दिक्कत है, गंभीर रूप से घायल है, या ज़हर की आशंका है, तो तुरंत आपातकालीन पशु-चिकित्सा मदद लें।\n\n"
        "अगर समस्या स्पष्ट नहीं है, तो पहले सबसे गंभीर संकेत देखें: साँस, खून, बेहोशी, तेज दर्द, ज़हर, या खड़ा न हो पाना।"
    ),
    "mr": (
        "आत्ता कनेक्ट होण्यात अडचण येत आहे. तोपर्यंत हे सुरक्षित मूलभूत टप्पे पाळा:\n\n"
        "1. आधी स्वतःची सुरक्षितता सांभाळा आणि कुत्र्याला कोपऱ्यात गाठू नका.\n"
        "2. कुत्रा उष्म्याने त्रस्त दिसत असेल तर त्याला सावलीत न्या आणि सुरक्षित असेल तर पाणी द्या.\n"
        "3. रक्तस्त्राव होत असेल तर स्वच्छ कापडाने थेट दाब द्या.\n"
        "4. कुत्रा कोसळला असेल, श्वास घेण्यास त्रास होत असेल, गंभीर जखमी असेल, किंवा विषबाधेची शक्यता असेल, तर त्वरित आपत्कालीन पशुवैद्यकीय मदत घ्या.\n\n"
        "समस्या स्पष्ट नसेल, तर आधी सर्वात गंभीर लक्षण तपासा: श्वास, रक्तस्त्राव, कोसळणे, तीव्र वेदना, विषबाधा, किंवा उभे राहता न येणे."
    ),
}


def _fallback_chat(message: str, context: str, language: str = "en") -> str:
    """Fallback response when the LLM is unavailable."""
    del message
    lang = language if language in ("en", "hi", "mr") else "en"
    if context and "No specific first aid articles" not in context:
        return _FALLBACK_WITH_KB[lang].format(context=context)
    return _FALLBACK_GENERIC[lang]
