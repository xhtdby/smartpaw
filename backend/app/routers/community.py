"""Community reporting and help-resource endpoints.

POST /api/report             - submit a dog sighting (with optional image)
GET  /api/reports            - fetch nearby reports
PATCH /api/reports/{id}      - update report status
GET  /api/reports/{id}/image - serve report image
GET  /api/nearby             - list verified rescue, official, and advice resources
"""

import json
import logging
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.config import get_settings
from app.database import get_report_by_id, get_reports_nearby, insert_report, update_report_status
from app.models.schemas import ReportResponse, ReportStatusUpdate, ShelterVet
from app.services.storage_guard import (
    StorageBudgetExceeded,
    StoredImageError,
    assert_storage_capacity,
    compress_image_for_storage,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["community"])

_resources: list[dict] = []
_RESOURCES_FILE = Path(__file__).parent.parent.parent / "data" / "help_resources.json"


def _load_resources():
    global _resources
    if not _resources and _RESOURCES_FILE.exists():
        with open(_RESOURCES_FILE, encoding="utf-8") as f:
            _resources = json.load(f)
        logger.info("Loaded %s verified help resources.", len(_resources))


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two lat/lng points."""
    radius = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


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
    """Submit a dog sighting with location, urgency, and optional image."""
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise HTTPException(status_code=400, detail="invalid_coordinates")

    if urgency not in ("low", "medium", "high", "critical"):
        raise HTTPException(status_code=400, detail="invalid_urgency")

    settings = get_settings()
    if len(description) > settings.report_description_max_chars:
        raise HTTPException(status_code=400, detail="description_too_long")

    image_filename = None
    image_storage_warning = None
    if image and image.content_type and image.content_type.startswith("image/"):
        image_bytes = await image.read()
        if len(image_bytes) > settings.max_image_size:
            raise HTTPException(status_code=400, detail="image_too_large")
        try:
            compressed = compress_image_for_storage(image_bytes, settings=settings)
            assert_storage_capacity(len(compressed), settings=settings)
            image_filename = f"{uuid.uuid4().hex}.jpg"
            filepath = _get_uploads_dir() / image_filename
            filepath.write_bytes(compressed)
        except StoredImageError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except StorageBudgetExceeded:
            logger.warning("Report image omitted because persistent storage budget is near full")
            image_storage_warning = "image_omitted_storage_limit"

    report_id = str(uuid.uuid4())
    entry = {
        "id": report_id,
        "latitude": latitude,
        "longitude": longitude,
        "description": description,
        "urgency": urgency,
        "image_filename": image_filename,
        "image_storage_warning": image_storage_warning,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "open",
    }
    await insert_report(entry)
    logger.info("New report created: %s - urgency: %s", report_id, urgency)

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
    if len(update.note) > get_settings().report_resolved_note_max_chars:
        raise HTTPException(status_code=400, detail="note_too_long")

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
    latitude: Optional[float] = Query(default=None, ge=-90, le=90),
    longitude: Optional[float] = Query(default=None, ge=-180, le=180),
    radius_km: float = Query(default=10.0, ge=0.1, le=50.0),
    type: Optional[str] = Query(default=None, description="Filter: rescue, official, advice"),
):
    """Return verified help resources.

    Location is optional because the data model is now a curated set of
    trustworthy rescue, official, and poison/advice resources rather than a
    misleading claim of full geocoded coverage for every city.
    """
    _load_resources()

    results = []
    for resource in _resources:
        if type and resource.get("type") != type:
            continue

        lat = resource.get("latitude")
        lon = resource.get("longitude")
        distance_km = None
        if latitude is not None and longitude is not None and lat is not None and lon is not None:
            dist = _haversine_km(latitude, longitude, lat, lon)
            if dist > radius_km:
                continue
            distance_km = round(dist, 2)

        results.append({**resource, "distance_km": distance_km})

    type_order = {"rescue": 0, "official": 1, "advice": 2}
    scope_order = {"regional": 0, "national": 1, "global": 2}
    results.sort(
        key=lambda item: (
            type_order.get(str(item.get("type")), 99),
            scope_order.get(str(item.get("scope")), 99),
            str(item.get("name", "")).lower(),
        )
    )
    return [ShelterVet(**item) for item in results]
