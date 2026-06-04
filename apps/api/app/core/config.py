from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:6543/postgres"
    supabase_url: str = ""
    supabase_service_key: str = ""
    openrouter_api_key: str = ""
    groq_api_key: str = ""
    youtube_api_key: str = ""
    storage_bucket: str = "thumbnails"
    sentry_dsn: str = ""
    free_whisper_daily_seconds: int = 3600  # 60 min for free plan
    allowed_origins: str = "http://localhost:3000"
    admin_secret: str = ""


settings = Settings()
# trigger
