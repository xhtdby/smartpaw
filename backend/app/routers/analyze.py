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
from app.services.medicine_kb import suggest_medicine_for_analysis
from app.services.response_generator import generate_fast_empathetic_response
from app.services.triage import heuristic_classify_situation
from app.services.vision_analyzer import analyze_vision, unavailable_result

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

UNAVAILABLE_MESSAGES = {
    "en": (
        "I could not analyze this photo right now because the vision model is unavailable. "
        "If the dog may be in danger, use the chat and describe what you can see."
    ),
    "hi": (
        "\u092b\u093f\u0932\u0939\u093e\u0932 \u092b\u094b\u091f\u094b \u0915\u093e \u0935\u093f\u0936\u094d\u0932\u0947\u0937\u0923 \u0928\u0939\u0940\u0902 \u0939\u094b \u0938\u0915\u093e \u0915\u094d\u092f\u094b\u0902\u0915\u093f \u0935\u093f\u091c\u0928 \u092e\u0949\u0921\u0932 \u0909\u092a\u0932\u092c\u094d\u0927 \u0928\u0939\u0940\u0902 \u0939\u0948\u0964 "
        "\u0905\u0917\u0930 \u0915\u0941\u0924\u094d\u0924\u093e \u0916\u0924\u0930\u0947 \u092e\u0947\u0902 \u0939\u094b \u0938\u0915\u0924\u093e \u0939\u0948, \u0924\u094b \u091a\u0948\u091f \u092e\u0947\u0902 \u091c\u094b \u0926\u093f\u0916 \u0930\u0939\u093e \u0939\u0948 \u0935\u0939 \u0932\u093f\u0916\u0947\u0902\u0964"
    ),
    "mr": (
        "\u0938\u0927\u094d\u092f\u093e \u092b\u094b\u091f\u094b\u091a\u0947 \u0935\u093f\u0936\u094d\u0932\u0947\u0937\u0923 \u0915\u0930\u0924\u093e \u0906\u0932\u0947 \u0928\u093e\u0939\u0940 \u0915\u093e\u0930\u0923 \u0935\u093f\u091c\u0928 \u092e\u0949\u0921\u0947\u0932 \u0909\u092a\u0932\u092c\u094d\u0927 \u0928\u093e\u0939\u0940\u0964 "
        "\u0915\u0941\u0924\u094d\u0930\u093e \u0927\u094b\u0915\u094d\u092f\u093e\u0924 \u0905\u0938\u0942 \u0936\u0915\u0924\u094b \u0905\u0938\u0947 \u0935\u093e\u091f\u0924 \u0905\u0938\u0947\u0932, \u0924\u0930 \u091a\u0945\u091f\u092e\u0927\u094d\u092f\u0947 \u0915\u093e\u092f \u0926\u093f\u0938\u0924\u0947 \u0924\u0947 \u0932\u093f\u0939\u093e\u0964"
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
        triage_questions=payload.get("triage_questions", []),
        empathetic_summary=payload.get("empathetic_summary", ""),
        when_to_call_professional=payload.get("when_to_call_professional", ""),
        approach_tips=payload.get("approach_tips", ""),
        disclaimer=payload.get("disclaimer", ""),
    )


def _ensure_payload_condition(payload: dict, condition_result: dict) -> dict:
    if "condition" not in payload or not isinstance(payload.get("condition"), dict):
        payload["condition"] = condition_result
    return payload


def _merge_context_triage(metadata: dict, user_context: str | None) -> dict:
    merged = {
        "analysis_status": metadata.get("analysis_status", "complete"),
        "species": metadata.get("species", "dog"),
        "urgency_signals": list(metadata.get("urgency_signals", [])),
        "unknown_factors": list(metadata.get("unknown_factors", [])),
        "scenario_type": metadata.get("scenario_type", "unclear"),
    }
    if not user_context or not user_context.strip():
        return merged

    triage = heuristic_classify_situation(user_context)
    if triage.species != "dog" or merged.get("species") in {"", "dog", None}:
        merged["species"] = triage.species
    if triage.scenario_type != "unclear":
        merged["scenario_type"] = triage.scenario_type
    if triage.urgency_tier in {"life_threatening", "urgent"}:
        signal = f"context_{triage.urgency_tier}"
        if signal not in merged["urgency_signals"]:
            merged["urgency_signals"].insert(0, signal)
    for fact in triage.missing_facts:
        if fact not in merged["unknown_factors"]:
            merged["unknown_factors"].append(fact)
    return merged


async def _run_vision_pipeline(
    image_bytes: bytes,
    confidence_threshold: float,
    user_context: str | None = None,
) -> tuple[dict | None, dict, dict, dict]:
    """Use the combined vision call first, then fall back to the legacy multi-call path."""
    settings = get_settings()
    if not settings.groq_api_key and not settings.hf_api_token:
        unavailable = unavailable_result()
        return None, unavailable["emotion"], unavailable["condition"], {
            "analysis_status": "unavailable",
            "species": unavailable.get("species", "other"),
            "urgency_signals": unavailable["urgency_signals"],
            "unknown_factors": unavailable["unknown_factors"],
            "scenario_type": unavailable["scenario_type"],
        }

    combined = await analyze_vision(image_bytes, user_context=user_context)
    if combined is not None:
        metadata = {
            "analysis_status": combined.get("analysis_status", "complete"),
            "species": combined.get("species", "dog"),
            "urgency_signals": combined.get("urgency_signals", []),
            "unknown_factors": combined.get("unknown_factors", []),
            "scenario_type": combined.get("scenario_type", "unclear"),
        }
        if not combined.get("dog_detected"):
            return None, combined.get("emotion", {}), combined.get("condition", {}), metadata
        return (
            {
                "confidence": combined.get("dog_confidence", 0.0),
                "description": combined.get("dog_description", ""),
            },
            combined.get("emotion", {}),
            combined.get("condition", {}),
            metadata,
        )

    logger.warning("Combined vision pipeline unavailable; falling back to legacy detection/emotion/condition calls.")
    detection = await detect_dog(image_bytes, confidence_threshold)
    if not detection:
        return None, {"label": "unknown", "confidence": 0.0, "description": "No dog visible"}, {}, {
            "analysis_status": "no_dog_visible",
            "species": "other",
            "urgency_signals": [],
            "unknown_factors": ["dog_not_visible"],
            "scenario_type": "no_dog_visible",
        }

    try:
        emotion_result = await classify_emotion(image_bytes)
    except Exception as exc:
        logger.error(f"Emotion classification failed: {exc}")
        emotion_result = {"label": "unknown", "confidence": 0.0, "description": "Could not determine emotion"}

    condition_result = await analyze_condition(image_bytes)
    return detection, emotion_result, condition_result, {
        "analysis_status": "uncertain",
        "species": "dog",
        "urgency_signals": [],
        "unknown_factors": [],
        "scenario_type": "unclear",
    }


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_dog_image(
    image: UploadFile = File(..., description="Photo of the dog"),
    language: str = Form(default="en", description="Response language: en, hi, mr"),
    user_context: str | None = Form(default=None, description="Optional scene details from the rescuer"),
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

    detection, emotion_result, condition_result, vision_metadata = await _run_vision_pipeline(
        image_bytes,
        settings.yolo_confidence,
        user_context,
    )
    vision_metadata = _merge_context_triage(vision_metadata, user_context)
    if not detection:
        analysis_status = vision_metadata.get("analysis_status", "no_dog_visible")
        summary = (
            UNAVAILABLE_MESSAGES.get(language, UNAVAILABLE_MESSAGES["en"])
            if analysis_status == "unavailable"
            else NO_DOG_MESSAGES.get(language, NO_DOG_MESSAGES["en"])
        )
        return AnalysisResponse(
            dog_detected=False,
            analysis_status=analysis_status,
            species=vision_metadata.get("species", "other"),
            empathetic_summary=summary,
            language=language,
            user_context=user_context,
            urgency_signals=vision_metadata.get("urgency_signals", []),
            unknown_factors=vision_metadata.get("unknown_factors", []),
            scenario_type=vision_metadata.get("scenario_type", "no_dog_visible"),
        )

    localized_payload = _ensure_payload_condition(
        generate_fast_empathetic_response(emotion_result, condition_result, language, user_context=user_context),
        condition_result,
    )
    localized_condition = localized_payload.get("condition", condition_result)
    otc_suggestion = suggest_medicine_for_analysis(
        vision_metadata.get("scenario_type", "unclear"),
        condition_result,
        user_context,
    )

    return AnalysisResponse(
        dog_detected=True,
        analysis_status=vision_metadata.get("analysis_status", "complete"),
        species=vision_metadata.get("species", "dog"),
        emotion=EmotionResult(
            label=emotion_result.get("label", "unknown"),
            confidence=emotion_result.get("confidence", 0.0),
        ),
        safety=SafetyLevel(
            level=localized_payload.get("safety_level", "caution"),
            reason=localized_payload.get("safety_reason", "Approach with care."),
        ),
        condition=_build_condition_assessment(localized_condition),
        user_context=user_context,
        urgency_signals=vision_metadata.get("urgency_signals", []),
        unknown_factors=vision_metadata.get("unknown_factors", []),
        scenario_type=vision_metadata.get("scenario_type", "unclear"),
        first_aid=_build_first_aid_steps(localized_payload.get("first_aid_steps", [])),
        triage_questions=localized_payload.get("triage_questions", []),
        empathetic_summary=localized_payload.get("empathetic_summary", ""),
        when_to_call_professional=localized_payload.get("when_to_call_professional", ""),
        approach_tips=localized_payload.get("approach_tips", ""),
        otc_suggestion=otc_suggestion,
        disclaimer=localized_payload.get("disclaimer", ""),
        language=language,
    )


@router.post("/analyze-multilingual", response_model=MultilingualAnalysisResponse)
async def analyze_dog_image_multilingual(
    image: UploadFile = File(..., description="Photo of the dog"),
    user_context: str | None = Form(default=None, description="Optional scene details from the rescuer"),
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

    detection, emotion_result, condition_result, vision_metadata = await _run_vision_pipeline(
        image_bytes,
        settings.yolo_confidence,
        user_context,
    )
    vision_metadata = _merge_context_triage(vision_metadata, user_context)
    if not detection:
        return MultilingualAnalysisResponse(
            dog_detected=False,
            analysis_status=vision_metadata.get("analysis_status", "no_dog_visible"),
            species=vision_metadata.get("species", "other"),
            user_context=user_context,
            urgency_signals=vision_metadata.get("urgency_signals", []),
            unknown_factors=vision_metadata.get("unknown_factors", []),
            scenario_type=vision_metadata.get("scenario_type", "no_dog_visible"),
        )

    en_raw, hi_raw, mr_raw = (
        generate_fast_empathetic_response(emotion_result, condition_result, "en", user_context=user_context),
        generate_fast_empathetic_response(emotion_result, condition_result, "hi", user_context=user_context),
        generate_fast_empathetic_response(emotion_result, condition_result, "mr", user_context=user_context),
    )
    en_payload = _ensure_payload_condition(en_raw, condition_result)
    hi_payload = _ensure_payload_condition(hi_raw, condition_result)
    mr_payload = _ensure_payload_condition(mr_raw, condition_result)
    otc_suggestion = suggest_medicine_for_analysis(
        vision_metadata.get("scenario_type", "unclear"),
        condition_result,
        user_context,
    )

    return MultilingualAnalysisResponse(
        dog_detected=True,
        analysis_status=vision_metadata.get("analysis_status", "complete"),
        species=vision_metadata.get("species", "dog"),
        emotion=EmotionResult(
            label=emotion_result.get("label", "unknown"),
            confidence=emotion_result.get("confidence", 0.0),
        ),
        condition=_build_condition_assessment(condition_result),
        user_context=user_context,
        urgency_signals=vision_metadata.get("urgency_signals", []),
        unknown_factors=vision_metadata.get("unknown_factors", []),
        scenario_type=vision_metadata.get("scenario_type", "unclear"),
        otc_suggestion=otc_suggestion,
        languages={
            "en": _build_language_result(en_payload),
            "hi": _build_language_result(hi_payload),
            "mr": _build_language_result(mr_payload),
        },
    )
