"""Community-drive coordination endpoints."""

from __future__ import annotations

import re
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from app.database import subscribe_mailing_list
from app.models.schemas import MailingListResponse, MailingListSubscribe

router = APIRouter(prefix="/api/mailing-list", tags=["community-drives"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ALLOWED_TAGS = {"food", "water", "medicine", "transport"}
_RATE_WINDOW_SECONDS = 60
_RATE_LIMIT = 8
_hits_by_ip: dict[str, deque[float]] = defaultdict(deque)


def _check_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    hits = _hits_by_ip[client_ip]
    while hits and now - hits[0] > _RATE_WINDOW_SECONDS:
        hits.popleft()
    if len(hits) >= _RATE_LIMIT:
        raise HTTPException(status_code=429, detail="rate_limited")
    hits.append(now)


@router.post("/subscribe", response_model=MailingListResponse)
async def subscribe(payload: MailingListSubscribe, request: Request):
    """Subscribe an email for manually coordinated local animal-care drives."""
    _check_rate_limit(request)

    email = payload.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="invalid_email")

    city = payload.city.strip()[:80] if payload.city and payload.city.strip() else None
    tags = []
    for tag in payload.interest_tags:
        normalized = tag.strip().lower()
        if normalized in _ALLOWED_TAGS and normalized not in tags:
            tags.append(normalized)

    timestamp = datetime.now(timezone.utc).isoformat()
    result = await subscribe_mailing_list(email, city, tags, timestamp)
    return MailingListResponse(**result)
