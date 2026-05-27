from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    supabase_url: str
    supabase_service_key: str
    openrouter_api_key: str
    openai_api_key: str
    cloudflare_r2_bucket: str = ""
    cloudflare_r2_endpoint: str = ""
    cloudflare_r2_access_key: str = ""
    cloudflare_r2_secret_key: str = ""
    sentry_dsn: str = ""


settings = Settings()
