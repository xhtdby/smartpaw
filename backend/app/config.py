from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache
from pathlib import Path


def _default_persistent_root() -> Path:
    """Prefer Railway mounted volume when available."""
    railway_data = Path("/app/data")
    if railway_data.exists() and railway_data.is_dir():
        return railway_data
    return Path(__file__).parent.parent / "data"


class Settings(BaseSettings):
    app_name: str = "IndieAid"
    debug: bool = False

    # Groq (free tier) — primary LLM/VLM provider
    groq_api_key: str = ""
    groq_vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    groq_text_model: str = "llama-3.3-70b-versatile"
    groq_triage_model: str = "llama-3.1-8b-instant"
    groq_judge_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"

    # HuggingFace Inference API — fallback
    hf_api_token: str = ""

    # Supabase (optional)
    supabase_url: str = ""
    supabase_key: str = ""

    # YOLO confidence threshold
    yolo_confidence: float = 0.4

    # Max image size (bytes) — 10 MB
    max_image_size: int = 10 * 1024 * 1024

    # Persist data under Railway volume when available
    data_dir: str = str(_default_persistent_root())

    # SQLite database path
    db_path: str = str(_default_persistent_root() / "indieaid.db")

    # Upload directory for report images
    uploads_dir: str = str(_default_persistent_root() / "uploads")

    # Allowed CORS origins
    cors_origins: list[str] = [
        "http://localhost:3000",
        "https://indieaid.vercel.app",
        "https://smartpaw.vercel.app",
    ]

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value):
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"release", "prod", "production"}:
                return False
        return value

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
