from app.services.response_generator import generate_fast_empathetic_response
from app.services.vision_analyzer import _normalize_result, unavailable_result


def test_unavailable_vision_payload_is_not_no_dog_visible():
    payload = unavailable_result()

    assert payload["dog_detected"] is False
    assert payload["analysis_status"] == "unavailable"
    assert payload["scenario_type"] == "analysis_unavailable"
    assert "analysis_unavailable" in payload["unknown_factors"]


def test_no_dog_visible_status_is_separate_from_unavailable():
    payload = _normalize_result(
        {
            "dog_detected": False,
            "dog_confidence": 0.1,
            "dog_description": "a room",
            "emotion": {"label": "unknown", "confidence": 0.0},
            "condition": {},
            "urgency_signals": [],
            "unknown_factors": ["dog_not_visible"],
            "scenario_type": "no_dog_visible",
        }
    )

    assert payload["analysis_status"] == "no_dog_visible"
    assert payload["scenario_type"] == "no_dog_visible"
    assert payload["condition"]["physical_condition"] == "No dog was visible in the image."


def test_healthy_fallback_is_warm_not_medical_report():
    payload = generate_fast_empathetic_response(
        {"label": "relaxed", "confidence": 0.8},
        {
            "breed_guess": "Indian pariah / mixed breed",
            "estimated_age": "adult",
            "physical_condition": "Looks alert with no obvious injury.",
            "visible_injuries": [],
            "health_concerns": [],
            "body_language": "relaxed",
        },
        "en",
    )

    assert payload["safety_level"] == "safe"
    assert payload["first_aid_steps"] == []
    assert "emergency" not in payload["empathetic_summary"].lower()
    assert "medical report" not in payload["empathetic_summary"].lower()


def test_context_emergency_overrides_healthy_photo_fallback():
    payload = generate_fast_empathetic_response(
        {"label": "relaxed", "confidence": 0.8},
        {
            "breed_guess": "Indian pariah / mixed breed",
            "estimated_age": "adult",
            "physical_condition": "Looks alert with no obvious injury.",
            "visible_injuries": [],
            "health_concerns": [],
            "body_language": "relaxed",
        },
        "en",
        user_context="dog was hit by a car and cannot stand",
    )

    assert payload["safety_level"] in {"caution", "danger"}
    assert "serious" in payload["empathetic_summary"].lower()
    assert len(payload["first_aid_steps"]) >= 3


def test_unavailable_fallback_is_multilingual():
    condition = {
        "breed_guess": "Unable to determine (analysis unavailable)",
        "estimated_age": "Unknown",
        "physical_condition": "Could not analyze - please consult a veterinarian.",
        "visible_injuries": [],
        "health_concerns": [],
        "body_language": "Could not analyze",
    }

    for language in ("en", "hi", "mr"):
        payload = generate_fast_empathetic_response({"label": "unknown", "confidence": 0.0}, condition, language)
        assert payload["safety_level"] == "caution"
        assert payload["first_aid_steps"] == []
        assert payload["info_sufficient"] is False
        if language != "en":
            assert any("\u0900" <= char <= "\u097F" for char in payload["empathetic_summary"])
