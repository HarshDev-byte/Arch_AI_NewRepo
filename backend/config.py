from pydantic_settings import BaseSettings

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
        env_file = ".env"

settings = Settings()
