"""Image analysis pipeline endpoint.

POST /api/analyze — upload a dog photo, receive a full empathetic assessment.
"""

import io
import logging
from PIL import Image
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.config import get_settings
from app.models.schemas import AnalysisResponse, EmotionResult, SafetyLevel, ConditionAssessment, FirstAidStep
from app.services.dog_detector import detect_dog
from app.services.emotion_classifier import classify_emotion
from app.services.condition_analyzer import analyze_condition
from app.services.response_generator import generate_empathetic_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["analyze"])

# Formats we accept and auto-convert
SUPPORTED_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "image/bmp", "image/tiff", "image/heic", "image/heif",
    "image/avif", "image/svg+xml", "image/x-icon",
}


def normalize_image(image_bytes: bytes) -> bytes:
    """Convert any supported image format to JPEG for consistent API processing."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        # Handle animated GIFs — take first frame
        if hasattr(img, "n_frames") and img.n_frames > 1:
            img.seek(0)
        # Convert RGBA/P/LA to RGB (strip alpha)
        if img.mode in ("RGBA", "P", "LA", "PA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        # Auto-orient based on EXIF data
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
        # Resize if too large (max 2048px on longest side) — reduces API latency
        max_dim = 2048
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()
    except Exception as e:
        logger.warning(f"Image normalization failed: {e}")
        return image_bytes


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_dog_image(
    image: UploadFile = File(..., description="Photo of the dog"),
    language: str = Form(default="en", description="Response language: en, hi, mr"),
):
    """Analyze a dog image for emotion, condition, safety, and first aid guidance."""
    settings = get_settings()

    # Accept any image type — we'll auto-convert
    content_type = (image.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file (JPEG, PNG, WebP, GIF, BMP, TIFF, HEIC, AVIF, etc.)")

    image_bytes = await image.read()

    if len(image_bytes) > settings.max_image_size:
        raise HTTPException(status_code=400, detail="Image too large. Please upload an image under 10 MB.")

    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    # Auto-convert to JPEG for consistent processing
    logger.info(f"Received image: {image.filename} ({content_type}, {len(image_bytes)} bytes)")
    image_bytes = normalize_image(image_bytes)
    logger.info(f"Normalized to JPEG: {len(image_bytes)} bytes")

    # Step 1: Detect dog
    logger.info("Step 1: Detecting dog in image...")
    detection = await detect_dog(image_bytes, settings.yolo_confidence)

    if not detection:
        return AnalysisResponse(
            dog_detected=False,
            empathetic_summary=(
                "We couldn't detect a dog in this photo. Could you try again with a clearer image? "
                "Make sure the dog is visible and well-lit. We're here to help! 🐾"
            ),
            language=language,
        )

    # Step 2: Classify emotion
    logger.info("Step 2: Classifying dog emotion...")
    try:
        emotion_result = await classify_emotion(image_bytes)
    except Exception as e:
        logger.error(f"Emotion classification failed: {e}")
        emotion_result = {"label": "unknown", "confidence": 0.0, "description": "Could not determine emotion"}

    # Step 3: Analyze condition via VLM
    logger.info("Step 3: Analyzing condition via VLM...")
    condition_result = await analyze_condition(image_bytes)

    # Step 4: Generate empathetic response
    logger.info("Step 4: Generating empathetic response...")
    response_data = await generate_empathetic_response(emotion_result, condition_result, language)

    # Build structured response
    first_aid_steps = [
        FirstAidStep(step_number=s["step_number"], instruction=s["instruction"])
        for s in response_data.get("first_aid_steps", [])
    ]

    return AnalysisResponse(
        dog_detected=True,
        emotion=EmotionResult(
            label=emotion_result["label"],
            confidence=emotion_result["confidence"],
        ),
        safety=SafetyLevel(
            level=response_data.get("safety_level", "caution"),
            reason=response_data.get("safety_reason", "Approach with care."),
        ),
        condition=ConditionAssessment(
            breed_guess=condition_result.get("breed_guess", "Unknown"),
            estimated_age=condition_result.get("estimated_age", "Unknown"),
            physical_condition=condition_result.get("physical_condition", ""),
            visible_injuries=condition_result.get("visible_injuries", []),
            health_concerns=condition_result.get("health_concerns", []),
            body_language=condition_result.get("body_language", ""),
        ),
        first_aid=first_aid_steps,
        empathetic_summary=response_data.get("empathetic_summary", ""),
        language=language,
    )
