from pathlib import Path
from pydantic_settings import BaseSettings

# Resolve .env relative to this file's location so it always finds the
# project-root .env regardless of which directory uvicorn is launched from.
_ROOT_ENV = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    # AI providers
    anthropic_api_key: str = ""
    groq_api_key: str = ""
    hf_api_key: str = ""             # huggingface.co/settings/tokens (free)

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_jwt_secret: str = ""    # Settings → API → JWT Secret in Supabase dashboard
    supabase_service_key: str = ""
    supabase_storage_bucket: str = "archai-models"  # bucket name in Supabase Storage
    # Default to a local SQLite DB for easier local development
    database_url: str = "sqlite:///./archai_dev.db"

    # Redis (Upstash)
    redis_url: str = ""

    # Qdrant vector memory
    qdrant_url: str = ""       # e.g. https://xyz.qdrant.io or http://localhost:6333
    qdrant_api_key: str = ""   # Qdrant Cloud API key (leave empty for local)

    # NREL solar/energy data
    nrel_api_key: str = ""

    # Mapbox
    mapbox_token: str = ""

    # Blender
    blender_path: str = "/usr/bin/blender"

    # Generation config
    max_design_variants: int = 5
    evolution_generations: int = 3
    enable_vr: bool = True

    # App
    environment: str = "development"
    app_url: str = "http://localhost:3000"
    next_public_api_url: str = "http://localhost:8000"
    next_public_app_url: str = "http://localhost:3000"
    next_public_mapbox_token: str = ""

    class Config:
        # Load from project-root .env; fall back to CWD .env if root not found
        env_file = str(_ROOT_ENV) if _ROOT_ENV.exists() else ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"            # silently ignore unknown env vars


settings = Settings()

