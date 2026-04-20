"""Dog emotion classifier using Groq Vision API.

Classifies dog emotions: happy, sad, angry, relaxed, fearful.
Replaces local HuggingFace transformers model to avoid heavy PyTorch dependency.
"""

import base64
import io
import json
import logging

import httpx
from PIL import Image

from app.config import get_settings
from app.services.groq_retry import groq_post_with_retry

logger = logging.getLogger(__name__)

EMOTION_PROMPT = """Analyze the emotional state of the dog in this image based on its body language, facial expression, posture, tail position, and ears.

Classify into exactly ONE of these emotions: happy, sad, angry, relaxed, fearful.

Respond ONLY with valid JSON in this exact format:
{"label": "happy", "confidence": 0.85, "description": "brief explanation of why you chose this emotion"}"""


async def classify_emotion(image_bytes: bytes) -> dict:
    """Classify the emotional state of the dog using Groq Vision API.

    Returns dict with:
      - label: str (e.g., "happy")
      - confidence: float (0-1)
      - description: str
    """
    settings = get_settings()
    if not settings.groq_api_key:
        logger.warning("Groq API key not configured.")
        return {"label": "unknown", "confidence": 0.0, "description": "Could not determine emotion"}

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=85)
    b64_image = base64.b64encode(buf.getvalue()).decode("utf-8")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await groq_post_with_retry(
                client,
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json_body={
                    "model": settings.groq_vision_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": EMOTION_PROMPT},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{b64_image}"
                                    },
                                },
                            ],
                        }
                    ],
                    "temperature": 0.2,
                    "max_tokens": 150,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()

            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]

            result = json.loads(content)

            label = result.get("label", "unknown").lower().strip()
            valid_labels = {"happy", "sad", "angry", "relaxed", "fearful"}
            if label not in valid_labels:
                label = "unknown"

            return {
                "label": label,
                "confidence": round(result.get("confidence", 0.5), 3),
                "description": result.get("description", f"This dog appears to be {label}"),
            }

    except Exception as e:
        logger.error(f"Emotion classification failed: {e}")
        return {"label": "unknown", "confidence": 0.0, "description": "Could not determine emotion"}
