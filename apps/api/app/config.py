from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://vepair:vepair@localhost:5432/vepair"
    app_env: str = "development"
    log_level: str = "INFO"
    api_cors_origins: str = "http://localhost:3000"

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    storage_backend: str = "local"
    storage_local_path: str = "./var/recordings"
    # Only used when storage_backend == "supabase". Must be a private bucket — recordings are
    # never served directly from Supabase; the backend always reads with the service role key
    # and re-serves bytes through our own authenticated/ownership-checked endpoint. See
    # PRIVACY.md's "no public-by-guessable-URL storage" principle.
    storage_bucket: str = "recordings"

    # Self-hosted auth (Stage 1). See app/auth.py for the Supabase swap point.
    jwt_secret: str = "dev-only-insecure-secret-change-me"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    password_reset_token_expire_minutes: int = 60

    # Outbound email. "log" (default) just logs the message server-side, matching the
    # dependency-free local-dev posture STORAGE_BACKEND=local uses. "graph" sends real mail via
    # Microsoft Graph (Microsoft 365), using OAuth2 client-credentials — not raw SMTP, since
    # Microsoft has been retiring Basic Auth for SMTP AUTH. See app/email.py.
    email_backend: str = "log"
    email_from_address: str = "noreply@vepair.com"
    ms_graph_tenant_id: str = ""
    ms_graph_client_id: str = ""
    ms_graph_client_secret: str = ""
    # Used to build links inside emails (e.g. the password-reset link) — never inferred from
    # API_CORS_ORIGINS, since that's a list and this needs to be the one canonical frontend URL.
    frontend_base_url: str = "http://localhost:3000"

    # Shared-secret auth for POST /api/v1/system/send-reminders -- an unattended daily job
    # (Cloud Scheduler) triggers this, and a human admin's 15-minute JWT is the wrong credential
    # for that. Empty by default so local dev/tests never accidentally leave it unset in a way
    # that's exploitable -- app/routers/system.py rejects every call when this is "".
    internal_job_secret: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
