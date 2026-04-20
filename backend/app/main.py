"""SmartPaw — Backend API

An empathetic AI assistant for helping stray dogs in Mumbai.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import analyze, community, chat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

app = FastAPI(
    title="SmartPaw API",
    description=(
        "AI-powered assistant for assessing stray dog conditions, "
        "providing first aid guidance, and connecting rescuers with shelters in Mumbai."
    ),
    version="1.0.0",
)

# CORS — allow the PWA frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://smartpaw.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router)
app.include_router(community.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    return {
        "name": "SmartPaw API",
        "version": "1.0.0",
        "message": "Helping Mumbai's stray dogs, one photo at a time. 🐾",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
