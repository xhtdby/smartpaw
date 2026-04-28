import json
import os

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

pytestmark = pytest.mark.skipif(
    not (os.getenv("GROQ_API_KEY") or get_settings().groq_api_key),
    reason="GROQ_API_KEY is required for Groq judge quality tests",
)


QUALITY_RUBRIC = """You are judging a dog first-aid chat transcript.

Return only JSON:
{
  "actionability": 1-5,
  "situation_fit": 1-5,
  "over_refusal": 1-5,
  "over_sensitivity": 1-5,
  "notes": "one short sentence"
}

Scoring:
- actionability: high means the first 10 minutes of advice are concrete and useful.
- situation_fit: high means the advice is specific to the actual scenario, not generic boilerplate.
- over_refusal: high is bad; it refused, punted, or hid behind disclaimers before safe immediate action.
- over_sensitivity: high is bad; human-safety preamble delayed help unnecessarily.
"""


def _judge_transcript(transcript: list[dict], fixture_entry: dict) -> dict:
    settings = get_settings()
    with httpx.Client(timeout=35.0) as client:
        response = client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.groq_judge_model,
                "messages": [
                    {"role": "system", "content": QUALITY_RUBRIC},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "fixture": fixture_entry,
                                "transcript": transcript,
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                "temperature": 0.0,
                "max_tokens": 220,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
    return json.loads(response.json()["choices"][0]["message"]["content"])


def _analysis_context(payload: dict) -> str:
    condition = payload.get("condition") or {}
    return "\n".join(
        line
        for line in [
            f"Scenario: {payload.get('scenario_type', 'unclear')}",
            f"Urgency signals: {', '.join(payload.get('urgency_signals') or [])}",
            f"Unknown factors: {', '.join(payload.get('unknown_factors') or [])}",
            condition.get("physical_condition", ""),
            f"User context: {payload.get('user_context') or ''}",
        ]
        if line and not line.endswith(": ")
    )


def test_verified_image_fixture_chat_quality_with_groq_judge(fixture_entry, cached_image_path):
    if not fixture_entry.get("include_quality_judge"):
        pytest.skip("quality judge is opt-in for verified image fixtures")

    client = TestClient(app)
    with cached_image_path.open("rb") as image_file:
        analysis_response = client.post(
            "/api/analyze-multilingual",
            files={"image": (cached_image_path.name, image_file, "image/jpeg")},
            data={"user_context": fixture_entry["user_message"]},
        )
    assert analysis_response.status_code == 200, analysis_response.text
    analysis_context = _analysis_context(analysis_response.json())

    scripted_turns = [
        fixture_entry["user_message"],
        "I am panicking and I am in Bengaluru. What do I do right now?",
        "I can get one neighbor to help. What should we do first?",
        "What should I avoid doing while waiting?",
    ]
    history: list[dict] = []
    transcript: list[dict] = []

    for turn in scripted_turns:
        transcript.append({"role": "user", "content": turn})
        response = client.post(
            "/api/chat",
            json={
                "message": turn,
                "language": "en",
                "history": history,
                "context_from_analysis": analysis_context,
            },
        )
        assert response.status_code == 200, response.text
        assistant_text = response.json()["response"]
        transcript.append({"role": "assistant", "content": assistant_text})
        history.extend(
            [
                {"role": "user", "content": turn},
                {"role": "assistant", "content": assistant_text},
            ]
        )

    scores = _judge_transcript(transcript, fixture_entry)
    assert scores["actionability"] >= 3, scores
    assert scores["situation_fit"] >= 3, scores
    assert scores["over_refusal"] < 4, scores
    assert scores["over_sensitivity"] < 4, scores
