from fastapi.testclient import TestClient

from app.main import app
from app.routers.chat import _build_triage_action_cards, _fallback_for_triage
from app.services.triage import TriageResult, _normalize_result, heuristic_classify_situation


def test_warm_messages_do_not_enter_emergency_triage():
    for message in ["hi", "what's up", "i have a cute dog"]:
        triage = heuristic_classify_situation(message)

        assert triage.urgency_tier == "low_risk"
        assert triage.scenario_type == "warm_conversation"


def test_casual_tone_does_not_hide_poisoning():
    triage = heuristic_classify_situation("my dog ate chocolate lol")

    assert triage.scenario_type == "poisoning"
    assert triage.urgency_tier == "urgent"


def test_hypothetical_chocolate_question_is_not_emergency_carded():
    triage = heuristic_classify_situation("can i feed chocolate to a dog")

    assert triage.scenario_type == "poisoning"
    assert triage.urgency_tier == "moderate"
    assert triage.intent == "medicine_question"

    cards, is_emergency = _build_triage_action_cards(
        "can i feed chocolate to a dog",
        "Do not feed chocolate.",
        "en",
        triage,
    )

    assert is_emergency is False
    assert [card["type"] for card in cards] == ["learn"]
    assert cards[0]["guide_id"] == "poison"


def test_code_mixed_weak_puppy_feeding_routes_to_feeding_guidance():
    triage = heuristic_classify_situation("ek nayi puppy mili hai bahut kamzor, kya khilau?")

    assert triage.scenario_type == "feeding_weak_dog"
    assert triage.urgency_tier == "moderate"

    reply = _fallback_for_triage("", "", triage)
    assert reply is not None
    assert "cow milk" in reply


def test_repair_intent_is_not_medical_triage():
    triage = heuristic_classify_situation("stop repeating yourself")

    assert triage.scenario_type == "conversation_repair"
    assert triage.urgency_tier == "low_risk"


def test_topic_redirect_with_active_symptom_is_care_not_repair():
    triage = heuristic_classify_situation("different dog now, he is limping badly")

    assert triage.scenario_type == "fracture"
    assert triage.mode == "care"


def test_anxious_apology_without_symptoms_routes_warm():
    triage = heuristic_classify_situation("sorry for asking so many questions, i get really worried")

    assert triage.scenario_type == "warm_conversation"
    assert triage.mode == "warm"


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


def test_medicine_intent_uses_medicine_card_not_gi_card():
    triage = TriageResult(
        urgency_tier="moderate",
        info_sufficient=True,
        scenario_type="vomiting_diarrhea",
        mode="care",
        intent="medicine_question",
    )

    cards, is_emergency = _build_triage_action_cards(
        "can I give a vomiting tablet?",
        "Do not give human medicine.",
        "en",
        triage,
    )

    assert is_emergency is False
    assert [card["type"] for card in cards] == ["learn"]
    assert cards[0]["guide_id"] == "poison"


def test_life_threatening_fracture_gets_emergency_and_find_help_cards():
    triage = TriageResult(
        urgency_tier="life_threatening",
        info_sufficient=True,
        scenario_type="fracture",
        mode="emergency",
    )

    cards, is_emergency = _build_triage_action_cards(
        "head bleeding and limping badly",
        "Keep still.",
        "en",
        triage,
    )

    assert is_emergency is True
    assert [card["type"] for card in cards] == ["emergency", "learn", "find_help"]
    assert cards[1]["guide_id"] == "trauma"


def test_llm_scenario_aliases_snap_to_canonical_and_preserve_intent():
    fallback = TriageResult(
        urgency_tier="moderate",
        info_sufficient=True,
        scenario_type="unsafe_medicine",
        mode="care",
        intent="medicine_question",
    )

    result = _normalize_result(
        {
            "urgency_tier": "moderate",
            "info_sufficient": True,
            "scenario_type": "gastrointestinal_issue",
            "mode": "care",
            "intent": "general",
        },
        fallback,
    )

    assert result.scenario_type == "vomiting_diarrhea"
    assert result.intent == "medicine_question"


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


# --- Stage 3: mode field ---


def test_mode_warm_on_greeting():
    for msg in ["hi", "hello", "what's up", "i have a cute dog"]:
        t = heuristic_classify_situation(msg)
        assert t.mode == "warm", f"Expected warm for {msg!r}, got {t.mode!r}"


def test_mode_emergency_on_road_trauma():
    t = heuristic_classify_situation("dog hit by car and cannot stand")
    assert t.mode == "emergency"


def test_mode_repair_on_correction():
    t = heuristic_classify_situation("stop repeating yourself")
    assert t.mode == "repair"


def test_mode_care_on_mild_diarrhea():
    t = heuristic_classify_situation("just started diarrhea no dehydration")
    assert t.mode == "care"


def test_mode_care_on_negated_symptom():
    t = heuristic_classify_situation("no seizure is happening")
    assert t.mode == "care"
    assert t.mode != "emergency"


# --- Stage 3: context_used ---


def test_context_used_false_without_context():
    t = heuristic_classify_situation("dog is limping")
    assert t.context_used is False


def test_context_used_true_when_message_references_context():
    t = heuristic_classify_situation(
        "what should i do",
        analysis_context="Dog has a bleeding wound on the leg.",
    )
    assert t.context_used is True


def test_context_used_false_when_message_is_self_sufficient():
    t = heuristic_classify_situation(
        "dog is limping",
        analysis_context="Dog has a bleeding wound on the leg.",
    )
    assert t.context_used is False


# --- Stage 3: Hindi/Marathi routing ---


def test_hindi_greeting_routes_warm():
    for msg in ["नमस्ते", "नमस्कार"]:
        t = heuristic_classify_situation(msg)
        assert t.scenario_type == "warm_conversation", f"Expected warm_conversation for {msg!r}"
        assert t.mode == "warm"


def test_code_mixed_diarrhea_routes_care():
    t = heuristic_classify_situation("dog ko diarrhea hua no dehydration")
    assert t.mode == "care"
    assert t.scenario_type == "vomiting_diarrhea"


def test_hindi_diarrhea_keyword_routes_care():
    t = heuristic_classify_situation("कुत्ते को दस्त लगे हैं कोई निर्जलीकरण नहीं")
    assert t.mode == "care"


def test_hindi_negation_does_not_route_emergency():
    t = heuristic_classify_situation("दौरा नहीं है")
    assert t.mode != "emergency"


def test_marathi_negation_does_not_route_emergency():
    t = heuristic_classify_situation("झटके येत नाहीत")
    assert t.mode != "emergency"


def test_hindi_road_trauma_routes_emergency():
    t = heuristic_classify_situation("कुत्ता गाड़ी से टकराया और खड़ा नहीं हो सकता")
    assert t.scenario_type == "road_trauma"
    assert t.mode == "emergency"


def test_marathi_road_trauma_routes_emergency():
    t = heuristic_classify_situation("कुत्र्याला गाडीने मारले आणि उभा राहू शकत नाही")
    assert t.scenario_type == "road_trauma"
    assert t.mode == "emergency"


def test_code_mixed_road_accident_routes_emergency():
    t = heuristic_classify_situation("mera dog road accident mein tha cannot stand")
    assert t.scenario_type == "road_trauma"
    assert t.mode == "emergency"


def test_previous_assistant_text_does_not_affect_mode():
    t = heuristic_classify_situation(
        "just started diarrhoea no dehydration",
        last_assistant_message="Eye injuries can worsen quickly. Watch for seizure, collapse, and bleeding.",
    )
    assert t.mode == "care"
    assert t.scenario_type == "vomiting_diarrhea"


def test_marathi_mild_symptom_routes_care():
    # "Dog is vomiting" in Marathi — should be care, not emergency
    t = heuristic_classify_situation("कुत्र्याला ओकारी आहे")
    assert t.mode == "care"
    assert t.scenario_type == "vomiting_diarrhea"


def test_marathi_repair_routes_repair():
    t = heuristic_classify_situation("हे चुकीचे आहे")
    assert t.mode == "repair"
    assert t.scenario_type == "conversation_repair"


def test_code_mixed_negation_does_not_route_emergency():
    # "no seizure" in English-Hindi code-mix; the English negation pattern strips it
    for msg in ["no seizure ho raha hai", "dog is not seizing koi problem nahi"]:
        t = heuristic_classify_situation(msg)
        assert t.mode != "emergency", f"Expected non-emergency for {msg!r}"


def test_deceased_pet_routes_to_stable_non_emergency_state():
    for msg in ["dead", "she\u2019s dead", "she's dead. remember?", "not an emergency, she's just dead"]:
        t = heuristic_classify_situation(msg)
        assert t.scenario_type == "deceased_pet", f"Expected deceased_pet for {msg!r}"
        assert t.mode == "care"
        assert t.urgency_tier == "low_risk"


def test_not_an_emergency_only_routes_repair():
    t = heuristic_classify_situation("not. an. emergency.")
    assert t.scenario_type == "conversation_repair"
    assert t.mode == "repair"


def test_deceased_pet_cards_stay_quiet():
    triage = heuristic_classify_situation("she\u2019s dead. remember?")
    cards, is_emergency = _build_triage_action_cards(
        "she\u2019s dead. remember?",
        "This does not need an emergency checklist.",
        "en",
        triage,
    )

    assert cards == []
    assert is_emergency is False


def test_cruelty_report_routes_to_cruelty_surface_not_emergency_cards():
    triage = heuristic_classify_situation("someone is beating a stray dog near my building")
    assert triage.scenario_type == "animal_cruelty_witnessed"
    assert triage.intent == "cruelty_witnessed"

    cards, is_emergency = _build_triage_action_cards(
        "someone is beating a stray dog near my building",
        "Document safely.",
        "en",
        triage,
    )

    assert is_emergency is False
    assert [card["type"] for card in cards] == ["cruelty", "find_help"]
    assert cards[0]["href"] == "/cruelty"


def test_chat_endpoint_deceased_pet_bypasses_emergency_flow():
    client = TestClient(app)
    response = client.post(
        "/api/chat",
        json={
            "message": "she\u2019s dead. remember?",
            "language": "en",
            "history": [
                {"role": "user", "content": "look at this cutie"},
                {
                    "role": "assistant",
                    "content": "What is your dog's name, and what brings you here today?",
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["triage"]["scenario_type"] == "deceased_pet"
    assert payload["triage"]["mode"] == "care"
    assert payload["is_emergency"] is False
    assert payload["action_cards"] == []
    assert "breathing" not in payload["response"].lower()
    assert "can stand" not in payload["response"].lower()
