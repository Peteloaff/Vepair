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

    # Self-hosted auth (Stage 1). See app/auth.py for the Supabase swap point.
    jwt_secret: str = "dev-only-insecure-secret-change-me"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    password_reset_token_expire_minutes: int = 60

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
