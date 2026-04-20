"""Dog emotion classifier using Dewa/dog_emotion_v3 from HuggingFace.

Classifies dog emotions: happy, sad, angry, relaxed, fearful.
Falls back to a simpler label set if model outputs differ.
"""

import io
import logging
from PIL import Image

logger = logging.getLogger(__name__)

_classifier = None


def _get_classifier():
    global _classifier
    if _classifier is None:
        from transformers import pipeline

        logger.info("Loading dog emotion classifier (Dewa/dog_emotion_v3)...")
        _classifier = pipeline(
            "image-classification",
            model="Dewa/dog_emotion_v3",
            top_k=5,
        )
    return _classifier


# Canonical emotion labels with friendly descriptions
EMOTION_DESCRIPTIONS = {
    "happy": "This dog appears happy and comfortable",
    "sad": "This dog seems sad or distressed",
    "angry": "This dog appears agitated or aggressive",
    "relaxed": "This dog looks calm and relaxed",
    "fearful": "This dog seems scared or anxious",
}


def classify_emotion(image_bytes: bytes) -> dict:
    """Classify the emotional state of the dog.

    Returns dict with:
      - label: str (e.g., "happy")
      - confidence: float (0-1)
      - description: str
      - all_scores: list of {label, score}
    """
    classifier = _get_classifier()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    results = classifier(image)

    top = results[0]
    label = top["label"].lower().strip()
    confidence = round(top["score"], 3)

    description = EMOTION_DESCRIPTIONS.get(
        label, f"This dog appears to be {label}"
    )

    return {
        "label": label,
        "confidence": confidence,
        "description": description,
        "all_scores": [
            {"label": r["label"].lower().strip(), "score": round(r["score"], 3)}
            for r in results
        ],
    }
