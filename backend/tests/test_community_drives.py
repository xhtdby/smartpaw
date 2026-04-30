from fastapi.testclient import TestClient

from app import database
from app.main import app
from app.routers.community_drives import _hits_by_ip


def test_mailing_list_subscribe_persists_and_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "_db_path", str(tmp_path / "indieaid-test.db"))
    _hits_by_ip.clear()

    with TestClient(app) as client:
        first = client.post(
            "/api/mailing-list/subscribe",
            json={
                "email": "Helper@Example.com",
                "city": "Pune",
                "interest_tags": ["food", "medicine", "food", "unknown"],
            },
        )
        assert first.status_code == 200
        assert first.json()["email"] == "helper@example.com"
        assert first.json()["city"] == "Pune"
        assert first.json()["interest_tags"] == ["food", "medicine"]

        second = client.post(
            "/api/mailing-list/subscribe",
            json={
                "email": "helper@example.com",
                "city": "Mumbai",
                "interest_tags": ["water"],
            },
        )
        assert second.status_code == 200
        payload = second.json()
        assert payload["city"] == "Mumbai"
        assert payload["interest_tags"] == ["water"]
        assert payload["created_at"] == first.json()["created_at"]
        assert payload["updated_at"] >= payload["created_at"]


def test_mailing_list_rejects_bad_email(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "_db_path", str(tmp_path / "indieaid-test.db"))
    _hits_by_ip.clear()

    with TestClient(app) as client:
        response = client.post(
            "/api/mailing-list/subscribe",
            json={"email": "not-an-email", "city": "Pune", "interest_tags": ["food"]},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_email"
