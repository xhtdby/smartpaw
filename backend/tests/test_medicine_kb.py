from types import SimpleNamespace
from urllib.parse import urlparse

from fastapi.testclient import TestClient

from app.main import app
from app.routers import chat as chat_router
from app.routers.chat import _build_system_prompt
from app.services.medicine_kb import (
    find_medicine_entry,
    format_medicine_fallback,
    load_medicine_kb,
)
from app.services.triage import TriageResult, heuristic_classify_situation


REQUIRED_ENTRY_KEYS = {
    "id",
    "names",
    "species_safe",
    "species_unsafe",
    "home_use_ok",
    "requires_vet",
    "dose_guidance",
    "status",
    "typical_use",
    "common_misuse",
    "guidance",
    "friendly_next_step",
    "safer_alternatives",
    "red_flags",
    "sources",
}


def test_medicine_kb_entries_are_sourced_and_structured():
    entries = load_medicine_kb()
    assert entries
    assert len({entry["id"] for entry in entries}) == len(entries)

    for entry in entries:
        assert REQUIRED_ENTRY_KEYS.issubset(entry), entry.get("id")
        assert entry["names"], entry["id"]
        assert entry["guidance"], entry["id"]
        assert entry["sources"], entry["id"]
        for source in entry["sources"]:
            parsed = urlparse(source["url"])
            assert parsed.scheme in {"http", "https"}, (entry["id"], source["url"])
            assert parsed.netloc, (entry["id"], source["url"])
            assert source.get("accessed_on") == "2026-04-30"
            assert source.get("claim_scope")


def test_medicine_kb_alias_matching_prefers_exact_known_entries():
    assert find_medicine_entry("can I give Crocin to this dog?")["id"] == "paracetamol"
    assert find_medicine_entry("is sugar-free gum safe for a dog?")["id"] == "xylitol"
    assert find_medicine_entry("can I rinse with Betadine?")["id"] == "povidone_iodine"
    assert find_medicine_entry("should I give Pedialyte?")["id"] == "oral_electrolyte_solution"


def test_medicine_prompt_uses_kb_as_authority():
    triage = TriageResult(
        urgency_tier="moderate",
        info_sufficient=True,
        scenario_type="unsafe_medicine",
        mode="care",
        intent="medicine_question",
    )

    system = _build_system_prompt(
        triage,
        "Respond in English.",
        "general first aid",
        "",
        '{"id": "paracetamol", "guidance": "Do not give."}',
    )

    assert "MEDICINE KB" in system
    assert "Do not invent doses" in system
    assert "paracetamol" in system


def test_medicine_fallback_without_verified_match_does_not_invent_doses():
    reply = format_medicine_fallback(None).lower()

    assert "verified entry" in reply
    assert "do not give" in reply
    assert "mg" not in reply


def test_hypothetical_chocolate_chat_is_sourced_without_emergency_cards(monkeypatch):
    monkeypatch.setattr(chat_router, "get_settings", lambda: SimpleNamespace(groq_api_key=""))
    client = TestClient(app)

    response = client.post(
        "/api/chat",
        json={"message": "can I feed chocolate to a dog?", "language": "en", "history": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["medicine"]["id"] == "chocolate"
    assert payload["is_emergency"] is False
    assert [card["type"] for card in payload["action_cards"]] == ["learn"]
    assert payload["medicine"]["sources"][0]["url"].startswith("https://www.fda.gov/")


def test_known_human_medicine_chat_returns_sourced_do_not_give(monkeypatch):
    monkeypatch.setattr(chat_router, "get_settings", lambda: SimpleNamespace(groq_api_key=""))
    client = TestClient(app)

    response = client.post(
        "/api/chat",
        json={"message": "can I give Crocin to my dog?", "language": "en", "history": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["triage"]["intent"] == "medicine_question"
    assert payload["medicine"]["id"] == "paracetamol"
    assert "do not give" in payload["response"].lower()
    assert any("Merck" in source for source in payload["sources"])


def test_known_toxin_exposure_attaches_medicine_payload(monkeypatch):
    monkeypatch.setattr(chat_router, "get_settings", lambda: SimpleNamespace(groq_api_key=""))
    triage = heuristic_classify_situation("my dog ate chocolate")
    assert triage.scenario_type == "poisoning"
    assert triage.intent == "general"

    client = TestClient(app)
    response = client.post(
        "/api/chat",
        json={"message": "my dog ate chocolate", "language": "en", "history": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["medicine"]["id"] == "chocolate"
    assert payload["is_emergency"] is True
    assert "call a veterinarian" in payload["response"].lower()
