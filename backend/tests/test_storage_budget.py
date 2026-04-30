import asyncio
from io import BytesIO
from types import SimpleNamespace

import aiosqlite
from fastapi.testclient import TestClient
from PIL import Image

from app import database
from app.main import app
from app.routers import community
from app.services.storage_guard import (
    TEXT_GZIP_PREFIX,
    compress_image_for_storage,
    decode_markdown_text_lossless,
    encode_markdown_text_lossless,
)


def _settings(tmp_path, soft_limit_mb=450):
    data_dir = tmp_path / "data"
    uploads_dir = data_dir / "uploads"
    return SimpleNamespace(
        data_dir=str(data_dir),
        db_path=str(data_dir / "indieaid-test.db"),
        uploads_dir=str(uploads_dir),
        max_image_size=10 * 1024 * 1024,
        persistent_storage_budget_mb=500,
        persistent_storage_soft_limit_mb=soft_limit_mb,
        persistent_storage_min_free_mb=1,
        stored_report_image_max_edge=960,
        stored_report_image_quality=68,
        stored_report_image_target_kb=220,
        stored_report_image_hard_max_kb=450,
        report_description_max_chars=4000,
        report_resolved_note_max_chars=2000,
    )


def _png_bytes(size=(2200, 1500)) -> bytes:
    image = Image.effect_noise(size, 80).convert("RGB")
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_markdown_text_codec_is_lossless_and_compacts_repetitive_text():
    markdown = ("# Update\n\n- rescued safely\n- needs follow up\n\n" * 200).strip()

    encoded = encode_markdown_text_lossless(markdown)

    assert encoded.startswith(TEXT_GZIP_PREFIX)
    assert len(encoded.encode("utf-8")) < len(markdown.encode("utf-8"))
    assert decode_markdown_text_lossless(encoded) == markdown


def test_report_image_compression_bounds_uploaded_images(tmp_path):
    settings = _settings(tmp_path)

    compressed = compress_image_for_storage(_png_bytes(), settings=settings)

    assert len(compressed) <= settings.stored_report_image_hard_max_kb * 1024
    assert Image.open(BytesIO(compressed)).format == "JPEG"


def test_report_description_is_stored_compactly_and_read_losslessly(tmp_path, monkeypatch):
    asyncio.run(_assert_report_description_roundtrip(tmp_path, monkeypatch))


async def _assert_report_description_roundtrip(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    monkeypatch.setattr(database, "_db_path", settings.db_path)
    await database.init_db()

    description = ("**Rescue note**\n\nThis puppy needs a foster and follow-up.\n" * 200).strip()
    report = {
        "id": "report-1",
        "latitude": 18.52,
        "longitude": 73.85,
        "description": description,
        "urgency": "medium",
        "image_filename": None,
        "created_at": "2026-04-30T00:00:00+00:00",
        "status": "open",
    }

    await database.insert_report(report)

    async with aiosqlite.connect(settings.db_path) as db:
        row = await db.execute("SELECT description FROM reports WHERE id = ?", ("report-1",))
        stored = (await row.fetchone())[0]

    assert stored.startswith(TEXT_GZIP_PREFIX)
    assert (await database.get_report_by_id("report-1"))["description"] == description


def test_report_endpoint_recompresses_images_before_disk_write(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    monkeypatch.setattr(database, "_db_path", settings.db_path)
    monkeypatch.setattr(community, "get_settings", lambda: settings)

    with TestClient(app) as client:
        response = client.post(
            "/api/report",
            data={
                "latitude": "18.52",
                "longitude": "73.85",
                "description": "Dog near the lane, stable but needs follow-up.",
                "urgency": "medium",
            },
            files={"image": ("report.png", _png_bytes(), "image/png")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["image_filename"].endswith(".jpg")
    saved = settings.uploads_dir and (tmp_path / "data" / "uploads" / payload["image_filename"])
    assert saved.exists()
    assert saved.stat().st_size <= settings.stored_report_image_hard_max_kb * 1024


def test_report_endpoint_omits_image_when_storage_budget_is_full(tmp_path, monkeypatch):
    settings = _settings(tmp_path, soft_limit_mb=0)
    monkeypatch.setattr(database, "_db_path", settings.db_path)
    monkeypatch.setattr(community, "get_settings", lambda: settings)

    with TestClient(app) as client:
        response = client.post(
            "/api/report",
            data={
                "latitude": "18.52",
                "longitude": "73.85",
                "description": "The animal is safe for now.",
                "urgency": "low",
            },
            files={"image": ("report.png", _png_bytes(), "image/png")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["image_filename"] is None
    assert payload["image_storage_warning"] == "image_omitted_storage_limit"
