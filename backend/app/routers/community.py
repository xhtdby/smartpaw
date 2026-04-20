"""Community reporting and nearby shelter/vet endpoints.

POST /api/report           — submit a stray dog sighting (with optional image)
GET  /api/reports          — fetch nearby reports
PATCH /api/reports/{id}    — update report status
GET  /api/reports/{id}/image — serve report image
GET  /api/nearby           — find nearby vets, shelters, NGOs
"""

import json
import logging
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse

from app.config import get_settings
from app.models.schemas import ReportResponse, ReportStatusUpdate, ShelterVet
from app.database import insert_report, get_reports_nearby, update_report_status, get_report_by_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["community"])

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


def _get_uploads_dir() -> Path:
    uploads = Path(get_settings().uploads_dir)
    uploads.mkdir(parents=True, exist_ok=True)
    return uploads


@router.post("/report", response_model=ReportResponse)
async def create_report(
    latitude: float = Form(...),
    longitude: float = Form(...),
    description: str = Form(default=""),
    urgency: str = Form(default="medium"),
    image: Optional[UploadFile] = File(default=None),
):
    """Submit a stray dog sighting with location, urgency, and optional image."""
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise HTTPException(status_code=400, detail="Invalid coordinates.")

    if urgency not in ("low", "medium", "high", "critical"):
        raise HTTPException(status_code=400, detail="Urgency must be low, medium, high, or critical.")

    # Handle optional image upload
    image_filename = None
    if image and image.content_type and image.content_type.startswith("image/"):
        ext = image.filename.rsplit(".", 1)[-1] if image.filename and "." in image.filename else "jpg"
        if ext.lower() not in ("jpg", "jpeg", "png", "webp"):
            ext = "jpg"
        image_filename = f"{uuid.uuid4().hex}.{ext}"
        image_bytes = await image.read()
        if len(image_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image too large (max 10 MB).")
        filepath = _get_uploads_dir() / image_filename
        filepath.write_bytes(image_bytes)

    report_id = str(uuid.uuid4())
    entry = {
        "id": report_id,
        "latitude": latitude,
        "longitude": longitude,
        "description": description,
        "urgency": urgency,
        "image_filename": image_filename,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "open",
    }
    await insert_report(entry)
    logger.info(f"New report created: {report_id} — urgency: {urgency}")

    return ReportResponse(**entry)


@router.get("/reports", response_model=list[ReportResponse])
async def list_reports(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=5.0, ge=0.1, le=50.0),
    urgency: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    """Fetch reports near a given location."""
    results = await get_reports_nearby(latitude, longitude, radius_km, urgency, status)
    return [ReportResponse(**r) for r in results]


@router.patch("/reports/{report_id}", response_model=ReportResponse)
async def update_status(report_id: str, update: ReportStatusUpdate):
    """Update the status of a report."""
    valid_statuses = ("open", "in_progress", "resolved", "closed")
    if update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {', '.join(valid_statuses)}")

    result = await update_report_status(report_id, update.status, update.note)
    if not result:
        raise HTTPException(status_code=404, detail="Report not found.")
    return ReportResponse(**result)


@router.get("/reports/{report_id}/image")
async def get_report_image(report_id: str):
    """Serve a report's attached image."""
    report = await get_report_by_id(report_id)
    if not report or not report.get("image_filename"):
        raise HTTPException(status_code=404, detail="Image not found.")

    filepath = _get_uploads_dir() / report["image_filename"]
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Image file missing.")

    return FileResponse(filepath)


@router.get("/nearby", response_model=list[ShelterVet])
async def find_nearby(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=10.0, ge=0.1, le=50.0),
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
