import os
import re

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

pytestmark = pytest.mark.skipif(
    not (os.getenv("GROQ_API_KEY") or get_settings().groq_api_key),
    reason="GROQ_API_KEY is required for image-based triage tests",
)


OVER_REFUSAL_PHRASES = [
    "i cannot help",
    "as an ai",
    "i am unable to",
    "consult a vet first",
    "cannot provide",
]


def _analysis_context(payload: dict) -> str:
    if not payload.get("dog_detected"):
        return "No dog detected in the uploaded image."

    condition = payload.get("condition") or {}
    lines = [
        f"Scenario: {payload.get('scenario_type', 'unclear')}",
        f"Urgency signals: {', '.join(payload.get('urgency_signals') or [])}",
        f"Unknown factors: {', '.join(payload.get('unknown_factors') or [])}",
        f"Breed: {condition.get('breed_guess', 'unknown')}",
        condition.get("physical_condition", ""),
        f"Injuries: {', '.join(condition.get('visible_injuries') or [])}",
        f"Concerns: {', '.join(condition.get('health_concerns') or [])}",
        f"User context: {payload.get('user_context') or ''}",
    ]
    return "\n".join(line for line in lines if line and not line.endswith(": "))


def test_image_analysis_and_chat_triage_contract(fixture_entry, cached_image_path):
    client = TestClient(app)

    with cached_image_path.open("rb") as image_file:
        analysis_response = client.post(
            "/api/analyze-multilingual",
            files={"image": (cached_image_path.name, image_file, "image/jpeg")},
            data={"user_context": fixture_entry["user_message"]},
        )
    assert analysis_response.status_code == 200, analysis_response.text
    analysis = analysis_response.json()

    assert analysis.get("scenario_type") == fixture_entry["scenario_type"]
    if fixture_entry["expected_urgency_tier"] in {"life_threatening", "urgent"}:
        assert analysis.get("urgency_signals"), "urgent fixtures should expose urgency signals"

    chat_response = client.post(
        "/api/chat",
        json={
            "message": fixture_entry["user_message"],
            "language": "en",
            "history": [],
            "context_from_analysis": _analysis_context(analysis),
        },
    )
    assert chat_response.status_code == 200, chat_response.text
    chat = chat_response.json()
    reply = chat["response"]
    reply_lower = reply.lower()

    assert chat["triage"]["urgency_tier"] == fixture_entry["expected_urgency_tier"]
    if fixture_entry.get("expects_numbered_first_aid"):
        assert re.search(r"(^|\n)\s*1\.", reply[:250]), reply[:250]

    for keyword in fixture_entry.get("must_mention_keywords", []):
        assert keyword.lower() in reply_lower
    for phrase in fixture_entry.get("must_not_say_phrases", []) + OVER_REFUSAL_PHRASES:
        assert phrase.lower() not in reply_lower
