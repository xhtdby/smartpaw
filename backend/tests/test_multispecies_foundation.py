from io import BytesIO
from types import SimpleNamespace

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.routers import analyze as analyze_router
from app.routers import chat as chat_router
from app.routers import community as community_router
from app.routers.chat import _build_triage_action_cards
from app.services.triage import heuristic_classify_situation


def _jpeg_bytes() -> bytes:
    image = Image.new("RGB", (12, 12), color=(220, 210, 200))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_cat_urinary_obstruction_is_life_threatening():
    triage = heuristic_classify_situation("my cat is straining to pee and no urine is coming")

    assert triage.species == "cat"
    assert triage.scenario_type == "cat_urinary_obstruction"
    assert triage.urgency_tier == "life_threatening"
    assert triage.needs_helpline_first is False


def test_cat_lily_exposure_routes_to_poisoning_without_dog_advice():
    triage = heuristic_classify_situation("my cat licked lily pollen")

    assert triage.species == "cat"
    assert triage.scenario_type == "poisoning"
    assert triage.urgency_tier == "urgent"
    assert triage.intent == "medicine_question"


def test_cow_bloat_is_life_threatening_livestock_triage():
    triage = heuristic_classify_situation("cow has a bloated left side and is breathing hard")

    assert triage.species == "cow"
    assert triage.scenario_type == "cow_bloat"
    assert triage.urgency_tier == "life_threatening"
    assert triage.needs_helpline_first is True


def test_cow_emergency_cards_deep_link_to_livestock_resources():
    triage = heuristic_classify_situation("cow has a bloated left side and is breathing hard")

    cards, is_emergency = _build_triage_action_cards(
        "cow has a bloated left side and is breathing hard",
        "Get livestock help.",
        "en",
        triage,
    )

    assert is_emergency is True
    help_links = [card["href"] for card in cards if card["type"] in {"emergency", "find_help"}]
    assert help_links
    assert all(href == "/nearby?species=cow" for href in help_links)


def test_snakebite_preserves_detected_species():
    triage = heuristic_classify_situation("calf bitten by snake on the leg")

    assert triage.species == "cow"
    assert triage.scenario_type == "snakebite"
    assert triage.urgency_tier == "urgent"


def test_other_species_routes_to_conservative_general_care():
    triage = heuristic_classify_situation("injured bird cannot fly")

    assert triage.species == "other"
    assert triage.scenario_type == "general_animal_care"
    assert triage.urgency_tier == "moderate"


def test_chat_endpoint_returns_species_aware_emergency_fallback(monkeypatch):
    monkeypatch.setattr(chat_router, "get_settings", lambda: SimpleNamespace(groq_api_key=""))

    client = TestClient(app)
    response = client.post(
        "/api/chat",
        json={"message": "my cat is straining to pee and no urine is coming", "language": "en"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["triage"]["species"] == "cat"
    assert payload["triage"]["scenario_type"] == "cat_urinary_obstruction"
    assert payload["is_emergency"] is True
    assert "emergency veterinary care" in payload["response"].lower()
    assert "dog" not in payload["response"].lower()


def test_nearby_species_filter_prioritizes_livestock_resources():
    community_router._resources.clear()
    client = TestClient(app)
    response = client.get("/api/nearby?species=cow")

    assert response.status_code == 200
    payload = response.json()
    ids = [item["id"] for item in payload]
    assert "emri-1962-livestock" in ids
    assert "kisan-call-centre-livestock" in ids
    assert "friendicoes-delhi" not in ids
    assert payload[0]["id"] in {"emri-1962-livestock", "kisan-call-centre-livestock", "maharashtra-animal-husbandry", "resq-pune"}
    assert all("cow" in item["species"] for item in payload)


def test_nearby_species_filter_rejects_unknown_species():
    client = TestClient(app)
    response = client.get("/api/nearby?species=horse")

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_species"


def test_multilingual_analysis_preserves_non_dog_species(monkeypatch):
    condition = {
        "breed_guess": "domestic cat",
        "estimated_age": "adult",
        "physical_condition": "alert cat visible",
        "visible_injuries": [],
        "health_concerns": [],
        "body_language": "calm",
    }

    async def fake_run_vision_pipeline(image_bytes, confidence_threshold, user_context=None):
        return (
            {"confidence": 0.95, "description": "cat visible"},
            {"label": "relaxed", "confidence": 0.8, "description": "calm"},
            condition,
            {
                "analysis_status": "complete",
                "species": "cat",
                "urgency_signals": [],
                "unknown_factors": [],
                "scenario_type": "healthy_or_low_risk",
            },
        )

    def fake_response(emotion_result, condition_result, language, user_context=None):
        return {
            "condition": condition_result,
            "safety_level": "safe",
            "safety_reason": "No urgent signs visible.",
            "first_aid_steps": [],
            "triage_questions": [],
            "empathetic_summary": "The cat looks calm.",
            "when_to_call_professional": "Call a vet if symptoms appear.",
            "approach_tips": "Move slowly.",
            "disclaimer": "Not a diagnosis.",
        }

    monkeypatch.setattr(analyze_router, "_run_vision_pipeline", fake_run_vision_pipeline)
    monkeypatch.setattr(analyze_router, "generate_fast_empathetic_response", fake_response)

    client = TestClient(app)
    response = client.post(
        "/api/analyze-multilingual",
        files={"image": ("cat.jpg", _jpeg_bytes(), "image/jpeg")},
        data={"user_context": "cat seems okay"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["dog_detected"] is True
    assert payload["species"] == "cat"
    assert payload["condition"]["breed_guess"] == "domestic cat"
