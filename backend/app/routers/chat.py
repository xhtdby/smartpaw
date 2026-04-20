"""First aid chatbot endpoint using RAG + LLM.

POST /api/chat — conversational follow-up after image analysis.
Uses a curated first aid knowledge base for retrieval-augmented generation.
"""

import json
import logging
from pathlib import Path

import httpx

from fastapi import APIRouter

from app.config import get_settings
from app.models.schemas import ChatRequest, ChatMessage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

# Load first aid knowledge base
_knowledge_base: list[dict] = []
_KB_FILE = Path(__file__).parent.parent.parent / "data" / "first_aid_kb.json"


def _load_kb():
    global _knowledge_base
    if not _knowledge_base and _KB_FILE.exists():
        with open(_KB_FILE, encoding="utf-8") as f:
            _knowledge_base = json.load(f)
        logger.info(f"Loaded {len(_knowledge_base)} first aid articles.")


def _retrieve_relevant(query: str, top_k: int = 3) -> str:
    """Simple keyword-based retrieval from the knowledge base.

    In production, replace with proper vector embeddings + similarity search.
    """
    _load_kb()
    query_words = set(query.lower().split())

    scored = []
    for article in _knowledge_base:
        text = (article.get("title", "") + " " + article.get("content", "")).lower()
        overlap = sum(1 for w in query_words if w in text)
        if overlap > 0:
            scored.append((overlap, article))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    if not top:
        return "No specific first aid articles found for this query."

    context_parts = []
    for _, article in top:
        context_parts.append(f"**{article['title']}**\n{article['content']}")
    return "\n\n---\n\n".join(context_parts)


SYSTEM_PROMPT = """You are SmartPaw, a warm and compassionate AI assistant helping people care for stray dogs in Mumbai. You provide first aid guidance, emotional support, and practical advice.

IMPORTANT RULES:
- You are NOT a veterinarian. Always remind users to consult a professional for serious cases.
- Be warm, empathetic, and encouraging. The user is worried about a dog.
- Keep answers clear, practical, and culturally sensitive to Mumbai context.
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
    """Chat with SmartPaw about dog first aid and care."""
    settings = get_settings()

    # Retrieve relevant knowledge
    context = _retrieve_relevant(request.message)

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
            "sources": [],
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

            return {"response": reply, "sources": []}

    except Exception as e:
        logger.error(f"Chat failed: {e}")
        return {
            "response": _fallback_chat(request.message, context),
            "sources": [],
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
