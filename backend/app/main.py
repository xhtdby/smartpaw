"""SmartPaw — Backend API

An empathetic AI assistant for helping stray dogs in Mumbai.
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
from app.routers import analyze, community, chat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    logger.info("SmartPaw API starting up...")
    await init_db()
    uploads = Path(get_settings().uploads_dir)
    uploads.mkdir(parents=True, exist_ok=True)
    yield
    logger.info("SmartPaw API shutting down.")


settings = get_settings()

app = FastAPI(
    title="SmartPaw API",
    description=(
        "AI-powered assistant for assessing stray dog conditions, "
        "providing first aid guidance, and connecting rescuers with shelters in Mumbai."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    ms = round((time.time() - start) * 1000, 1)
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({ms}ms)")
    return response


# Serve uploaded report images
uploads_path = Path(settings.uploads_dir)
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

app.include_router(analyze.router)
app.include_router(community.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    return {
        "name": "SmartPaw API",
        "version": "2.0.0",
        "message": "Helping Mumbai's stray dogs, one photo at a time. 🐾",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
