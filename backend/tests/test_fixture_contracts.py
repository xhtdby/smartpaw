import json
from pathlib import Path

from app.routers.chat import _build_triage_action_cards
from app.services.triage import heuristic_classify_situation
from app.services.vision_analyzer import _normalize_result

FIXTURE_ROOT = Path(__file__).parent / "fixtures"


def _load_fixture_suite(name: str) -> list[dict]:
    return json.loads((FIXTURE_ROOT / name / "labels.json").read_text(encoding="utf-8"))


def test_router_fixtures_are_text_only_and_match_triage_contract():
    for fixture in _load_fixture_suite("router"):
        assert fixture["fixture_type"] == "text_router"
        assert "url" not in fixture

        triage = heuristic_classify_situation(fixture["user_message"])
        assert triage.scenario_type == fixture["scenario_type"], fixture["id"]
        assert triage.urgency_tier == fixture["expected_urgency_tier"], fixture["id"]

        cards, is_emergency = _build_triage_action_cards(
            fixture["user_message"],
            "Generated text should not decide cards.",
            "en",
            triage,
        )
        assert [card["type"] for card in cards] == fixture["expected_card_types"], fixture["id"]
        assert is_emergency is any(card_type == "emergency" for card_type in fixture["expected_card_types"])


def test_mock_vision_fixtures_normalize_without_network_or_image_claims():
    for fixture in _load_fixture_suite("mock_vision"):
        assert fixture["fixture_type"] == "mock_vision"
        assert "url" not in fixture

        normalized = _normalize_result(fixture["input"])
        expected = fixture["expected"]

        assert normalized["dog_detected"] is expected["dog_detected"], fixture["id"]
        assert normalized["scenario_type"] == expected["scenario_type"], fixture["id"]
        assert normalized["emotion"]["label"] == expected["emotion_label"], fixture["id"]

        if "urgency_signals" in expected:
            assert normalized["urgency_signals"] == expected["urgency_signals"], fixture["id"]
        if "visible_injuries" in expected:
            assert normalized["condition"]["visible_injuries"] == expected["visible_injuries"], fixture["id"]
        if "health_concerns" in expected:
            assert normalized["condition"]["health_concerns"] == expected["health_concerns"], fixture["id"]


def test_verified_image_suite_is_local_or_empty():
    for fixture in _load_fixture_suite("verified_images"):
        assert fixture["fixture_type"] == "verified_image"
        assert "url" not in fixture
        local_path = fixture.get("local_path")
        assert local_path, fixture["id"]
        assert (FIXTURE_ROOT / local_path).is_file(), fixture["id"]


def test_quarantined_external_fixtures_are_not_visual_truth_sources():
    quarantined = [
        FIXTURE_ROOT / "quarantined_external_quick" / "labels.json",
        FIXTURE_ROOT / "quarantined_external_detailed" / "labels.json",
    ]
    for path in quarantined:
        entries = json.loads(path.read_text(encoding="utf-8"))
        assert entries, path
        assert any("url" in entry for entry in entries)
