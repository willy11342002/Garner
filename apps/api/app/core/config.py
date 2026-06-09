from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:6543/postgres"
    supabase_url: str = ""
    supabase_service_key: str = ""
    openrouter_api_key: str = ""
    storage_bucket: str = "thumbnails"
    sentry_dsn: str = ""
    allowed_origins: str = "http://localhost:3000"
    apify_api_token: str = ""


settings = Settings()
# trigger
