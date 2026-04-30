from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.routers import analyze as analyze_router
from app.services.medicine_kb import suggest_medicine_for_analysis


def _jpeg_bytes() -> bytes:
    image = Image.new("RGB", (12, 12), color=(220, 210, 200))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_analysis_suggests_saline_for_visible_wound_context():
    suggestion = suggest_medicine_for_analysis(
        "maggot_wound",
        {
            "physical_condition": "open wound on hind leg",
            "visible_injuries": ["open wound"],
            "health_concerns": ["maggots"],
            "body_language": "guarded",
        },
    )

    assert suggestion is not None
    assert suggestion["id"] == "saline_wound_flush"
    assert suggestion["home_use_ok"] is True


def test_analysis_suggests_electrolyte_only_for_matching_gi_context():
    suggestion = suggest_medicine_for_analysis(
        "vomiting_diarrhea",
        {
            "physical_condition": "weak but alert",
            "visible_injuries": [],
            "health_concerns": ["diarrhea"],
            "body_language": "tired",
        },
        "dog has had diarrhea since morning",
    )

    assert suggestion is not None
    assert suggestion["id"] == "oral_electrolyte_solution"
    assert suggestion["requires_vet"] is False


def test_multilingual_analysis_response_includes_otc_suggestion(monkeypatch):
    condition = {
        "breed_guess": "Unknown",
        "estimated_age": "adult",
        "physical_condition": "open wound on leg",
        "visible_injuries": ["open wound"],
        "health_concerns": ["maggots"],
        "body_language": "guarded",
    }

    async def fake_run_vision_pipeline(image_bytes, confidence_threshold, user_context=None):
        return (
            {"confidence": 0.95, "description": "dog visible"},
            {"label": "fearful", "confidence": 0.7, "description": "fearful"},
            condition,
            {
                "analysis_status": "complete",
                "urgency_signals": [],
                "unknown_factors": [],
                "scenario_type": "maggot_wound",
            },
        )

    def fake_response(emotion_result, condition_result, language, user_context=None):
        return {
            "condition": condition_result,
            "safety_level": "caution",
            "safety_reason": "Approach carefully.",
            "first_aid_steps": [{"step_number": 1, "instruction": "Keep the dog calm."}],
            "triage_questions": [],
            "empathetic_summary": "This looks uncomfortable.",
            "when_to_call_professional": "Call if the wound is deep or painful.",
            "approach_tips": "Move slowly.",
            "disclaimer": "Not a diagnosis.",
        }

    monkeypatch.setattr(analyze_router, "_run_vision_pipeline", fake_run_vision_pipeline)
    monkeypatch.setattr(analyze_router, "generate_fast_empathetic_response", fake_response)

    client = TestClient(app)
    response = client.post(
        "/api/analyze-multilingual",
        files={"image": ("dog.jpg", _jpeg_bytes(), "image/jpeg")},
        data={"user_context": "there are maggots in an open wound"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["otc_suggestion"]["id"] == "saline_wound_flush"
    assert payload["otc_suggestion"]["sources"][0]["url"].startswith("https://")
