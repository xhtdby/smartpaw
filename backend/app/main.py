"""IndieAid backend API.

Grounded AI guidance for pets and community animals.
"""

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db
from app.routers import analyze, community, chat, community_drives
from app.services.storage_guard import check_writable, storage_snapshot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    del app
    logger.info("IndieAid API starting up...")
    await init_db()
    uploads = Path(get_settings().uploads_dir)
    uploads.mkdir(parents=True, exist_ok=True)
    yield
    logger.info("IndieAid API shutting down.")


settings = get_settings()

app = FastAPI(
    title="IndieAid API",
    description=(
        "AI-powered guidance for assessing dog conditions, providing grounded "
        "first-aid steps, and connecting rescuers with verified help resources."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    ms = round((time.time() - start) * 1000, 1)
    logger.info("%s %s -> %s (%sms)", request.method, request.url.path, response.status_code, ms)
    return response


uploads_path = Path(settings.uploads_dir)
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

app.include_router(analyze.router)
app.include_router(community.router)
app.include_router(community_drives.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    return {
        "name": "IndieAid API",
        "version": "2.0.0",
        "message": "Grounded AI help for pets and community animals.",
    }


@app.get("/health")
async def health():
    settings = get_settings()
    snapshot = storage_snapshot(settings)
    db_path = Path(snapshot["db_path"])
    uploads_dir = Path(snapshot["uploads_dir"])
    return {
        "status": "ok",
        "db_path": str(db_path),
        "uploads_dir": str(uploads_dir),
        "db_exists": db_path.exists(),
        "db_writable": check_writable(db_path.parent),
        "uploads_writable": check_writable(uploads_dir),
        "storage_budget_mb": settings.persistent_storage_budget_mb,
        "storage_soft_limit_mb": settings.persistent_storage_soft_limit_mb,
        "storage_used_mb": round(snapshot["used_bytes"] / (1024 * 1024), 2),
        "storage_remaining_soft_mb": round(snapshot["remaining_soft_bytes"] / (1024 * 1024), 2),
        "disk_free_mb": round(snapshot["disk_free_bytes"] / (1024 * 1024), 2),
    }
