"""Community reporting and nearby shelter/vet endpoints.

POST /api/report     — submit a stray dog sighting
GET  /api/reports    — fetch nearby reports
GET  /api/nearby     — find nearby vets, shelters, NGOs
"""

import json
import logging
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import ReportCreate, ReportResponse, ShelterVet

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["community"])

# In-memory store (replace with Supabase in production)
_reports: list[dict] = []

# Load shelter/vet data
_shelters: list[dict] = []
_SHELTERS_FILE = Path(__file__).parent.parent.parent / "data" / "shelters_mumbai.json"


def _load_shelters():
    global _shelters
    if not _shelters and _SHELTERS_FILE.exists():
        with open(_SHELTERS_FILE, encoding="utf-8") as f:
            _shelters = json.load(f)
        logger.info(f"Loaded {len(_shelters)} shelters/vets from seed data.")


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two lat/lng points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@router.post("/report", response_model=ReportResponse)
async def create_report(report: ReportCreate):
    """Submit a stray dog sighting with location and urgency."""
    if not (-90 <= report.latitude <= 90 and -180 <= report.longitude <= 180):
        raise HTTPException(status_code=400, detail="Invalid coordinates.")

    entry = {
        "id": str(uuid.uuid4()),
        "latitude": report.latitude,
        "longitude": report.longitude,
        "description": report.description,
        "urgency": report.urgency,
        "image_url": report.image_url,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "open",
    }
    _reports.append(entry)
    logger.info(f"New report created: {entry['id']} — urgency: {report.urgency}")
    return ReportResponse(**entry)


@router.get("/reports", response_model=list[ReportResponse])
async def list_reports(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=5.0, ge=0.1, le=50.0),
    urgency: Optional[str] = Query(default=None),
):
    """Fetch reports near a given location."""
    results = []
    for r in _reports:
        dist = _haversine_km(latitude, longitude, r["latitude"], r["longitude"])
        if dist <= radius_km:
            if urgency and r["urgency"] != urgency:
                continue
            results.append(r)

    # Sort by newest first
    results.sort(key=lambda x: x["created_at"], reverse=True)
    return [ReportResponse(**r) for r in results]


@router.get("/nearby", response_model=list[ShelterVet])
async def find_nearby(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=5.0, ge=0.1, le=50.0),
    type: Optional[str] = Query(default=None, description="Filter: vet, shelter, ngo"),
):
    """Find nearby vets, shelters, and NGOs."""
    _load_shelters()

    results = []
    for s in _shelters:
        if type and s.get("type") != type:
            continue
        dist = _haversine_km(latitude, longitude, s["latitude"], s["longitude"])
        if dist <= radius_km:
            results.append({**s, "distance_km": round(dist, 2)})

    results.sort(key=lambda x: x["distance_km"])
    return [ShelterVet(**r) for r in results]
