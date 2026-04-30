"""Sourced medicine and OTC first-aid knowledge base helpers."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

MEDICINE_KB_FILE = Path(__file__).parent.parent.parent / "data" / "medicine_kb.json"


@lru_cache
def load_medicine_kb() -> list[dict[str, Any]]:
    if not MEDICINE_KB_FILE.exists():
        return []
    with open(MEDICINE_KB_FILE, encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        return []
    return [entry for entry in data if isinstance(entry, dict)]


def _normalize(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"[^a-z0-9\s+-]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def find_medicine_entry(message: str) -> dict[str, Any] | None:
    normalized = _normalize(message)
    if not normalized:
        return None

    best: tuple[int, dict[str, Any]] | None = None
    for entry in load_medicine_kb():
        names = [str(name).lower() for name in entry.get("names", []) if str(name).strip()]
        for name in sorted(names, key=len, reverse=True):
            needle = _normalize(name)
            if not needle:
                continue
            pattern = rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])"
            if re.search(pattern, normalized):
                score = len(needle)
                if best is None or score > best[0]:
                    best = (score, entry)
    return dict(best[1]) if best else None


def medicine_sources(entry: dict[str, Any] | None) -> list[str]:
    if not entry:
        return []
    titles: list[str] = []
    for source in entry.get("sources", []):
        title = str(source.get("title", "")).strip() if isinstance(source, dict) else ""
        if title:
            titles.append(title)
    return titles


def medicine_public_payload(entry: dict[str, Any] | None) -> dict[str, Any] | None:
    if not entry:
        return None
    sources = [
        {
            "title": str(source.get("title", "")).strip(),
            "url": str(source.get("url", "")).strip(),
        }
        for source in entry.get("sources", [])
        if isinstance(source, dict) and source.get("title") and source.get("url")
    ]
    return {
        "id": entry.get("id", ""),
        "status": entry.get("status", ""),
        "home_use_ok": bool(entry.get("home_use_ok", False)),
        "requires_vet": bool(entry.get("requires_vet", True)),
        "guidance": entry.get("guidance", ""),
        "friendly_next_step": entry.get("friendly_next_step", ""),
        "safer_alternatives": entry.get("safer_alternatives", []),
        "red_flags": entry.get("red_flags", []),
        "sources": sources,
    }


def medicine_context(entry: dict[str, Any] | None) -> str:
    if not entry:
        return "No exact medicine KB match. Do not invent dosing; explain that a vet should confirm medicine safety."
    payload = medicine_public_payload(entry) or {}
    return json.dumps(payload, ensure_ascii=False, indent=2)


def format_medicine_fallback(entry: dict[str, Any] | None) -> str:
    if not entry:
        return (
            "I do not have a verified entry for that medicine yet. Please do not give it until a veterinarian confirms it is safe for this animal. "
            "If anything was already swallowed, note the name, strength, amount, and time, then call a vet or poison service."
        )

    lines = [
        str(entry.get("guidance", "")).strip(),
        str(entry.get("friendly_next_step", "")).strip(),
    ]
    alternatives = [str(item).strip() for item in entry.get("safer_alternatives", []) if str(item).strip()]
    red_flags = [str(item).strip() for item in entry.get("red_flags", []) if str(item).strip()]
    if alternatives:
        lines.append("Safer options: " + ", ".join(alternatives[:3]) + ".")
    if red_flags:
        lines.append("Get urgent help if you see: " + ", ".join(red_flags[:5]) + ".")

    sources = medicine_sources(entry)
    if sources:
        lines.append("Source: " + sources[0] + ".")
    return "\n".join(line for line in lines if line)
