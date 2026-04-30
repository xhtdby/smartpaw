"""SQLite database layer for IndieAid.

Handles report persistence and image metadata.
Uses aiosqlite for async compatibility with FastAPI.
"""

import aiosqlite
import json
import logging
from pathlib import Path

from app.config import get_settings
from app.services.storage_guard import decode_markdown_text_lossless, encode_markdown_text_lossless

logger = logging.getLogger(__name__)

_db_path: str | None = None


def _migrate_legacy_db_path(target_path: str) -> None:
    target = Path(target_path)
    legacy = target.with_name("smartpaw.db")
    if target.exists() or not legacy.exists():
        return

    try:
        legacy.rename(target)
        logger.info(f"Migrated legacy database from {legacy} to {target}")
    except Exception as exc:
        logger.warning(f"Could not migrate legacy database from {legacy} to {target}: {exc}")


def _get_db_path() -> str:
    global _db_path
    if _db_path is None:
        _db_path = get_settings().db_path
        _migrate_legacy_db_path(_db_path)
    return _db_path


def _decode_report_fields(report: dict) -> dict:
    decoded = dict(report)
    decoded["description"] = decode_markdown_text_lossless(decoded.get("description"))
    decoded["resolved_note"] = decode_markdown_text_lossless(decoded.get("resolved_note"))
    return decoded


async def init_db():
    """Create tables if they don't exist."""
    db_path = _get_db_path()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                urgency TEXT NOT NULL DEFAULT 'medium',
                image_filename TEXT,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                resolved_at TEXT,
                resolved_note TEXT
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_reports_location
            ON reports (latitude, longitude)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_reports_status
            ON reports (status)
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mailing_list (
                email TEXT PRIMARY KEY,
                city TEXT,
                interest_tags TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        await db.commit()
        logger.info(f"Database initialized at {db_path}")


async def insert_report(report: dict) -> dict:
    """Insert a new report and return it."""
    db_path = _get_db_path()
    stored_report = {
        **report,
        "description": encode_markdown_text_lossless(report.get("description")),
    }
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO reports (id, latitude, longitude, description, urgency,
               image_filename, created_at, status)
               VALUES (:id, :latitude, :longitude, :description, :urgency,
               :image_filename, :created_at, :status)""",
            stored_report,
        )
        await db.commit()
    return report


async def get_reports_nearby(
    lat: float, lng: float, radius_km: float,
    urgency: str | None = None, status: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Fetch reports near a location. Uses bounding box pre-filter + haversine."""
    import math

    # Rough bounding box (1 degree ≈ 111 km)
    delta = radius_km / 111.0
    min_lat, max_lat = lat - delta, lat + delta
    min_lng, max_lng = lng - delta, lng + delta

    db_path = _get_db_path()
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT * FROM reports
            WHERE latitude BETWEEN ? AND ?
            AND longitude BETWEEN ? AND ?
        """
        params: list = [min_lat, max_lat, min_lng, max_lng]

        if urgency:
            query += " AND urgency = ?"
            params.append(urgency)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = await db.execute(query, params)
        results = []
        async for row in rows:
            r = dict(row)
            # Haversine check
            dlat = math.radians(r["latitude"] - lat)
            dlng = math.radians(r["longitude"] - lng)
            a = (
                math.sin(dlat / 2) ** 2
                + math.cos(math.radians(lat))
                * math.cos(math.radians(r["latitude"]))
                * math.sin(dlng / 2) ** 2
            )
            dist = 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            if dist <= radius_km:
                results.append(_decode_report_fields(r))

        return results


async def update_report_status(report_id: str, status: str, note: str = "") -> dict | None:
    """Update a report's status. Returns updated report or None if not found."""
    from datetime import datetime, timezone

    db_path = _get_db_path()
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        resolved_at = datetime.now(timezone.utc).isoformat() if status in ("resolved", "closed") else None
        encoded_note = encode_markdown_text_lossless(note)
        await db.execute(
            """UPDATE reports SET status = ?, resolved_at = ?, resolved_note = ?
               WHERE id = ?""",
            (status, resolved_at, encoded_note, report_id),
        )
        await db.commit()

        row = await db.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
        result = await row.fetchone()
        return _decode_report_fields(dict(result)) if result else None


async def get_report_by_id(report_id: str) -> dict | None:
    """Get a single report by ID."""
    db_path = _get_db_path()
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        row = await db.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
        result = await row.fetchone()
        return _decode_report_fields(dict(result)) if result else None


async def subscribe_mailing_list(
    email: str,
    city: str | None,
    interest_tags: list[str],
    timestamp: str,
) -> dict:
    """Create or update a drive coordination mailing-list subscription."""
    normalized_email = email.strip().lower()
    tags_json = json.dumps(interest_tags, ensure_ascii=False)
    db_path = _get_db_path()
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """
            INSERT INTO mailing_list (email, city, interest_tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                city = excluded.city,
                interest_tags = excluded.interest_tags,
                updated_at = excluded.updated_at
            """,
            (normalized_email, city, tags_json, timestamp, timestamp),
        )
        await db.commit()
        row = await db.execute("SELECT * FROM mailing_list WHERE email = ?", (normalized_email,))
        result = await row.fetchone()
        if not result:
            raise RuntimeError("mailing_list_subscription_missing_after_insert")
        data = dict(result)
        data["interest_tags"] = json.loads(data.get("interest_tags") or "[]")
        return data
