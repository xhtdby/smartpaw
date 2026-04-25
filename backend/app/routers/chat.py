"""First aid chatbot endpoint using RAG + LLM.

POST /api/chat — conversational follow-up after image analysis.
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
from app.models.schemas import ChatRequest, ChatMessage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

# Load first aid knowledge base
_knowledge_base: list[dict] = []
_idf_cache: dict[str, float] = {}
_KB_FILE = Path(__file__).parent.parent.parent / "data" / "first_aid_kb.json"

# Common stop words to filter out
_STOP_WORDS = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would shall should may might can could to of in for on with "
    "at by from it its this that these those i me my we our you your "
    "he she they them their what which who whom how and or but not no".split()
)


def _tokenize(text: str) -> list[str]:
    """Lowercase tokenization with stop word removal."""
    words = re.findall(r"[a-z]+", text.lower())
    return [w for w in words if w not in _STOP_WORDS and len(w) > 1]


def _load_kb():
    global _knowledge_base, _idf_cache
    if not _knowledge_base and _KB_FILE.exists():
        with open(_KB_FILE, encoding="utf-8") as f:
            _knowledge_base = json.load(f)
        logger.info(f"Loaded {len(_knowledge_base)} first aid articles.")

        # Pre-compute IDF scores
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
    """TF-IDF-inspired retrieval with tag boosting from the knowledge base.

    Returns (context_text, source_titles).
    """
    _load_kb()
    query_tokens = _tokenize(query)
    if not query_tokens:
        return "No specific first aid articles found for this query.", []

    query_tf = Counter(query_tokens)

    scored = []
    for article in _knowledge_base:
        text = article.get("title", "") + " " + article.get("content", "")
        tags = article.get("tags", [])

        # TF-IDF score for content
        doc_tokens = _tokenize(text)
        doc_tf = Counter(doc_tokens)
        score = 0.0
        for word, q_count in query_tf.items():
            if word in doc_tf:
                tf = 1 + math.log(doc_tf[word]) if doc_tf[word] > 0 else 0
                idf = _idf_cache.get(word, 1.0)
                score += q_count * tf * idf

        # Tag boost: exact tag match gets a 3x bonus
        for tag in tags:
            tag_lower = tag.lower()
            for qt in query_tokens:
                if qt in tag_lower:
                    score += 5.0

        if score > 0:
            scored.append((score, article))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    if not top:
        return "No specific first aid articles found for this query.", []

    context_parts = []
    sources = []
    for _, article in top:
        context_parts.append(f"**{article['title']}**\n{article['content']}")
        sources.append(article["title"])
    return "\n\n---\n\n".join(context_parts), sources


SYSTEM_PROMPT = """You are IndieAid, a warm and compassionate AI assistant helping people care for stray dogs in India. You provide first aid guidance, emotional support, and practical advice using Indian-specific treatments and resources.

IMPORTANT RULES:
- You are NOT a veterinarian. Always remind users to consult a professional for serious cases.
- Suggest India-specific remedies like diluted Betadine, Neosporin, or Arnica 200 when appropriate.
- Be warm, empathetic, and encouraging. The user is worried about a dog.
- Keep answers clear, practical, and culturally sensitive to the Indian context.
- If the user speaks in Hindi or Marathi, respond in that language.
- Use the knowledge base context below to give accurate first aid information.

{language_instruction}

KNOWLEDGE BASE CONTEXT:
{context}"""

LANGUAGE_INSTRUCTIONS = {
    "en": "Respond in English.",
    "hi": "Respond in Hindi (Devanagari script).",
    "mr": "Respond in Marathi (Devanagari script).",
}


@router.post("/chat")
async def chat(request: ChatRequest):
    """Chat with IndieAid about dog first aid and care."""
    settings = get_settings()

    # Retrieve relevant knowledge
    context, sources = _retrieve_relevant(request.message)

    # Add analysis context if provided
    if request.context_from_analysis:
        context = f"Previous analysis of the dog:\n{request.context_from_analysis}\n\n---\n\n{context}"

    lang_instruction = LANGUAGE_INSTRUCTIONS.get(request.language, LANGUAGE_INSTRUCTIONS["en"])
    system = SYSTEM_PROMPT.format(language_instruction=lang_instruction, context=context)

    # Build message history
    messages = [{"role": "system", "content": system}]
    for msg in request.history[-10:]:  # Keep last 10 messages for context
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})

    if not settings.groq_api_key:
        return {
            "response": _fallback_chat(request.message, context),
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
                    "temperature": 0.6,
                    "max_tokens": 800,
                },
            )
            response.raise_for_status()
            data = response.json()
            reply = data["choices"][0]["message"]["content"]

            return {"response": reply, "sources": sources}

    except Exception as e:
        logger.error(f"Chat failed: {e}")
        return {
            "response": _fallback_chat(request.message, context),
            "sources": sources,
        }


def _fallback_chat(message: str, context: str) -> str:
    """Simple fallback when LLM is unavailable."""
    if context and "No specific first aid articles" not in context:
        return (
            "I'm having trouble connecting to my AI brain right now, but here's "
            "what I found in my knowledge base:\n\n"
            f"{context}\n\n"
            "If you need immediate help, please call an animal rescue helpline or visit the nearest vet."
        )
    return (
        "I'm sorry, I'm having trouble connecting right now. "
        "For immediate help with an injured dog, please:\n\n"
        "1. Keep the dog calm and avoid sudden movements\n"
        "2. Offer water from a safe distance\n"
        "3. Call a local animal rescue helpline\n"
        "4. Contact the nearest veterinary clinic\n\n"
        "You're doing a great thing by caring. The dog is lucky you stopped. 🐾"
    )
