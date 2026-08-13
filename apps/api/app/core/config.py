from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    debug: bool = False  # DEBUG=true → 本地開發把 log 層級設為 DEBUG

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:6543/postgres"
    supabase_url: str = ""
    supabase_service_key: str = ""
    openrouter_api_key: str = ""
    storage_bucket: str = "thumbnails"
    sentry_dsn: str = ""
    allowed_origins: str = "http://localhost:3000"
    apify_api_token: str = ""
    gumroad_seller_id: str = "ZzkVkd8mJG6ZMVGAikCwGg=="
    gumroad_access_token: str = ""
    gumroad_webhook_url: str = ""  # e.g. https://garner-api.fly.dev/billing/webhook
    gumroad_client_id: str = ""
    gumroad_client_secret: str = ""
    # 沒有預設值是刻意的：這個值必須跟 Gumroad 後台註冊的 redirect URI 逐字相同，
    # 猜錯只會換來一個難查的 OAuth 錯誤。原本硬寫的 garner-brain.up.railway.app
    # 在 2026-08 後端搬到 Fly.io 之後就是死的網址，留著只會讓錯誤更難發現。
    gumroad_redirect_uri: str = ""
    google_maps_api_key: str = ""
    google_ai_api_key: str = ""  # Google AI Studio key — used for File API + direct Gemini calls
    admin_secret: str = ""  # X-Admin-Secret header value required by /admin/* endpoints


settings = Settings()
