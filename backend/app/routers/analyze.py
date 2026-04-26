"""Image analysis endpoints for single-language and multilingual responses."""

import io
import logging

from PIL import Image
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import get_settings
from app.models.schemas import (
    AnalysisResponse,
    ConditionAssessment,
    EmotionResult,
    FirstAidStep,
    LanguageResult,
    MultilingualAnalysisResponse,
    SafetyLevel,
)
from app.services.condition_analyzer import analyze_condition
from app.services.dog_detector import detect_dog
from app.services.emotion_classifier import classify_emotion
from app.services.response_generator import generate_empathetic_response, translate_analysis_payload
from app.services.vision_analyzer import analyze_vision

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["analyze"])


NO_DOG_MESSAGES = {
    "en": (
        "We couldn't detect a dog in this photo. Could you try again with a clearer image? "
        "Make sure the dog is visible and well-lit. We're here to help!"
    ),
    "hi": (
        "इस फोटो में हमें कुत्ता नहीं मिला। कृपया और साफ़ फोटो के साथ फिर से कोशिश करें। "
        "सुनिश्चित करें कि कुत्ता साफ दिखाई दे और रोशनी ठीक हो। हम मदद के लिए तैयार हैं!"
    ),
    "mr": (
        "या फोटोमध्ये आम्हाला कुत्रा दिसला नाही. कृपया अधिक स्पष्ट फोटोसह पुन्हा प्रयत्न करा. "
        "कुत्रा स्पष्ट दिसत आहे आणि प्रकाश पुरेसा आहे याची खात्री करा. आम्ही मदतीसाठी तयार आहोत!"
    ),
}


def normalize_image(image_bytes: bytes) -> bytes:
    """Convert supported image formats to JPEG for consistent model input."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if hasattr(img, "n_frames") and img.n_frames > 1:
            img.seek(0)
        if img.mode in ("RGBA", "P", "LA", "PA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        from PIL import ImageOps

        img = ImageOps.exif_transpose(img)
        max_dim = 2048
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()
    except Exception as exc:
        logger.warning(f"Image normalization failed: {exc}")
        return image_bytes


def _build_condition_assessment(condition_data: dict) -> ConditionAssessment:
    return ConditionAssessment(
        breed_guess=condition_data.get("breed_guess", "Unknown"),
        estimated_age=condition_data.get("estimated_age", "Unknown"),
        physical_condition=condition_data.get("physical_condition", ""),
        visible_injuries=condition_data.get("visible_injuries", []),
        health_concerns=condition_data.get("health_concerns", []),
        body_language=condition_data.get("body_language", ""),
    )


def _build_first_aid_steps(first_aid_data: list[dict]) -> list[FirstAidStep]:
    return [
        FirstAidStep(step_number=step["step_number"], instruction=step["instruction"])
        for step in first_aid_data
    ]


def _build_language_result(payload: dict) -> LanguageResult:
    return LanguageResult(
        condition=_build_condition_assessment(payload["condition"]),
        safety=SafetyLevel(
            level=payload.get("safety_level", "caution"),
            reason=payload.get("safety_reason", "Approach with care."),
        ),
        first_aid=_build_first_aid_steps(payload.get("first_aid_steps", [])),
        empathetic_summary=payload.get("empathetic_summary", ""),
        when_to_call_professional=payload.get("when_to_call_professional", ""),
        approach_tips=payload.get("approach_tips", ""),
        disclaimer=payload.get("disclaimer", ""),
    )


async def _run_vision_pipeline(image_bytes: bytes, confidence_threshold: float) -> tuple[dict | None, dict, dict]:
    """Use the combined vision call first, then fall back to the legacy multi-call path."""
    combined = await analyze_vision(image_bytes)
    if combined is not None:
        if not combined.get("dog_detected"):
            return None, combined.get("emotion", {}), combined.get("condition", {})
        return (
            {
                "confidence": combined.get("dog_confidence", 0.0),
                "description": combined.get("dog_description", ""),
            },
            combined.get("emotion", {}),
            combined.get("condition", {}),
        )

    logger.warning("Combined vision pipeline unavailable; falling back to legacy detection/emotion/condition calls.")
    detection = await detect_dog(image_bytes, confidence_threshold)
    if not detection:
        return None, {"label": "unknown", "confidence": 0.0, "description": "No dog visible"}, {}

    try:
        emotion_result = await classify_emotion(image_bytes)
    except Exception as exc:
        logger.error(f"Emotion classification failed: {exc}")
        emotion_result = {"label": "unknown", "confidence": 0.0, "description": "Could not determine emotion"}

    condition_result = await analyze_condition(image_bytes)
    return detection, emotion_result, condition_result


def _build_canonical_payload(condition_result: dict, response_data: dict, emotion_result: dict) -> dict:
    return {
        "emotion": {
            "label": emotion_result.get("label", "unknown"),
            "confidence": emotion_result.get("confidence", 0.0),
        },
        "condition": condition_result,
        "safety_level": response_data.get("safety_level", "caution"),
        "safety_reason": response_data.get("safety_reason", "Approach with care."),
        "empathetic_summary": response_data.get("empathetic_summary", ""),
        "first_aid_steps": response_data.get("first_aid_steps", []),
        "when_to_call_professional": response_data.get("when_to_call_professional", ""),
        "approach_tips": response_data.get("approach_tips", ""),
    }


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_dog_image(
    image: UploadFile = File(..., description="Photo of the dog"),
    language: str = Form(default="en", description="Response language: en, hi, mr"),
):
    """Analyze a dog image for emotion, condition, safety, and first aid guidance."""
    settings = get_settings()
    content_type = (image.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="image_invalid_format")

    image_bytes = await image.read()
    if len(image_bytes) > settings.max_image_size:
        raise HTTPException(status_code=400, detail="image_too_large")
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="image_empty")

    logger.info(f"Received image: {image.filename} ({content_type}, {len(image_bytes)} bytes)")
    image_bytes = normalize_image(image_bytes)
    logger.info(f"Normalized to JPEG: {len(image_bytes)} bytes")

    detection, emotion_result, condition_result = await _run_vision_pipeline(
        image_bytes,
        settings.yolo_confidence,
    )
    if not detection:
        return AnalysisResponse(
            dog_detected=False,
            empathetic_summary=NO_DOG_MESSAGES.get(language, NO_DOG_MESSAGES["en"]),
            language=language,
        )

    en_response = await generate_empathetic_response(emotion_result, condition_result, "en")
    canonical_payload = _build_canonical_payload(condition_result, en_response, emotion_result)
    localized_payload = await translate_analysis_payload(canonical_payload, language)

    return AnalysisResponse(
        dog_detected=True,
        emotion=EmotionResult(
            label=emotion_result.get("label", "unknown"),
            confidence=emotion_result.get("confidence", 0.0),
        ),
        safety=SafetyLevel(
            level=localized_payload.get("safety_level", "caution"),
            reason=localized_payload.get("safety_reason", "Approach with care."),
        ),
        condition=_build_condition_assessment(localized_payload["condition"]),
        first_aid=_build_first_aid_steps(localized_payload.get("first_aid_steps", [])),
        empathetic_summary=localized_payload.get("empathetic_summary", ""),
        disclaimer=localized_payload.get("disclaimer", ""),
        language=language,
    )


@router.post("/analyze-multilingual", response_model=MultilingualAnalysisResponse)
async def analyze_dog_image_multilingual(
    image: UploadFile = File(..., description="Photo of the dog"),
):
    """Run vision once, then build stored UI payloads for English, Hindi, and Marathi."""
    settings = get_settings()
    content_type = (image.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="image_invalid_format")

    image_bytes = await image.read()
    if len(image_bytes) > settings.max_image_size:
        raise HTTPException(status_code=400, detail="image_too_large")
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="image_empty")

    logger.info(f"Multilingual: received {image.filename} ({content_type}, {len(image_bytes)} bytes)")
    image_bytes = normalize_image(image_bytes)
    logger.info(f"Multilingual: normalized to JPEG {len(image_bytes)} bytes")

    detection, emotion_result, condition_result = await _run_vision_pipeline(
        image_bytes,
        settings.yolo_confidence,
    )
    if not detection:
        return MultilingualAnalysisResponse(dog_detected=False)

    en_response = await generate_empathetic_response(emotion_result, condition_result, "en")
    canonical_payload = _build_canonical_payload(condition_result, en_response, emotion_result)

    en_payload = await translate_analysis_payload(canonical_payload, "en")
    hi_payload = await translate_analysis_payload(canonical_payload, "hi")
    mr_payload = await translate_analysis_payload(canonical_payload, "mr")

    return MultilingualAnalysisResponse(
        dog_detected=True,
        emotion=EmotionResult(
            label=emotion_result.get("label", "unknown"),
            confidence=emotion_result.get("confidence", 0.0),
        ),
        condition=_build_condition_assessment(condition_result),
        languages={
            "en": _build_language_result(en_payload),
            "hi": _build_language_result(hi_payload),
            "mr": _build_language_result(mr_payload),
        },
    )
