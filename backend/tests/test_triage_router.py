from app.routers.chat import _build_triage_action_cards
from app.services.triage import TriageResult, heuristic_classify_situation


def test_warm_messages_do_not_enter_emergency_triage():
    for message in ["hi", "what's up", "i have a cute dog"]:
        triage = heuristic_classify_situation(message)

        assert triage.urgency_tier == "low_risk"
        assert triage.scenario_type == "warm_conversation"


def test_casual_tone_does_not_hide_poisoning():
    triage = heuristic_classify_situation("my dog ate chocolate lol")

    assert triage.scenario_type == "poisoning"
    assert triage.urgency_tier == "urgent"


def test_repair_intent_is_not_medical_triage():
    triage = heuristic_classify_situation("stop repeating yourself")

    assert triage.scenario_type == "conversation_repair"
    assert triage.urgency_tier == "low_risk"


def test_negated_seizure_clears_emergency_context():
    triage = heuristic_classify_situation("no seizure is happening")

    assert triage.scenario_type == "symptom_negated"
    assert triage.urgency_tier == "low_risk"


def test_previous_assistant_text_does_not_poison_current_turn():
    triage = heuristic_classify_situation(
        "just started diarrhoea no dehydration",
        last_assistant_message="Eye injuries can worsen quickly. Watch for seizure, collapse, and bleeding.",
    )

    assert triage.scenario_type == "vomiting_diarrhea"
    assert triage.urgency_tier == "moderate"


def test_current_message_can_override_stale_analysis_context():
    triage = heuristic_classify_situation(
        "just started diarrhoea no dehydration",
        analysis_context="Scenario: eye_injury. The dog has a swollen bleeding eye.",
    )

    assert triage.scenario_type == "vomiting_diarrhea"
    assert triage.urgency_tier == "moderate"


def test_action_cards_do_not_mine_assistant_warning_text_for_warm_turns():
    triage = TriageResult(
        urgency_tier="low_risk",
        info_sufficient=True,
        scenario_type="warm_conversation",
    )

    cards, is_emergency = _build_triage_action_cards(
        "i have a cute dog",
        "Watch for vomiting, wounds, collapse, diarrhea, or breathing trouble.",
        "en",
        triage,
    )

    assert cards == []
    assert is_emergency is False


def test_action_cards_follow_triage_for_mild_diarrhea():
    triage = heuristic_classify_situation("just started diarrhea no dehydration")

    cards, is_emergency = _build_triage_action_cards(
        "just started diarrhea no dehydration",
        "Generic warning text mentioning trauma, poisoning, and emergency.",
        "en",
        triage,
    )

    assert is_emergency is False
    assert [card["type"] for card in cards] == ["learn"]
    assert cards[0]["guide_id"] == "puppies"


def test_true_road_trauma_gets_emergency_cards():
    triage = heuristic_classify_situation("dog hit by bike and cannot stand")

    cards, is_emergency = _build_triage_action_cards(
        "dog hit by bike and cannot stand",
        "Keep still.",
        "en",
        triage,
    )

    assert triage.scenario_type == "road_trauma"
    assert is_emergency is True
    assert "emergency" in [card["type"] for card in cards]
    assert "find_help" in [card["type"] for card in cards]
