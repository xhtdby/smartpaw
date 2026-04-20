"""Dog detection service using Groq Vision API.

Validates that a dog is present in the uploaded image before running
further analysis. Replaces local YOLOv8 to avoid heavy PyTorch dependency.
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

DETECTION_PROMPT = """Look at this image carefully. Is there a dog visible in this image?

Respond ONLY with valid JSON in this exact format:
{"dog_detected": true, "confidence": 0.95, "description": "brief description of the dog"}

If no dog is visible, respond:
{"dog_detected": false, "confidence": 0.0, "description": "what is in the image instead"}"""


async def detect_dog(image_bytes: bytes, confidence_threshold: float = 0.4) -> dict | None:
    """Detect a dog in the image using Groq Vision API.

    Returns dict with keys: confidence, description if a dog is found,
    otherwise returns None.
    """
    settings = get_settings()
    if not settings.groq_api_key:
        logger.warning("Groq API key not configured, skipping detection.")
        return None

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
                                {"type": "text", "text": DETECTION_PROMPT},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{b64_image}"
                                    },
                                },
                            ],
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 150,
                },
            )
            if response.status_code != 200:
                logger.error(f"Groq API error {response.status_code}: {response.text[:500]}")
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Extract JSON
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]

            result = json.loads(content)

            if result.get("dog_detected") and result.get("confidence", 0) >= confidence_threshold:
                logger.info(f"Dog detected with confidence {result['confidence']}")
                return {
                    "confidence": round(result["confidence"], 3),
                    "description": result.get("description", ""),
                }

            logger.info("No dog detected in the image.")
            return None

    except Exception as e:
        logger.error(f"Dog detection failed: {e}")
        return None
