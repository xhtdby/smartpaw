from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "SmartPaw"
    debug: bool = False

    # Groq (free tier) — primary LLM/VLM provider
    groq_api_key: str = ""
    groq_vision_model: str = "llama-3.2-90b-vision-preview"
    groq_text_model: str = "llama-3.1-8b-instant"

    # HuggingFace Inference API — fallback
    hf_api_token: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""

    # YOLO confidence threshold
    yolo_confidence: float = 0.4

    # Max image size (bytes) — 10 MB
    max_image_size: int = 10 * 1024 * 1024

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
