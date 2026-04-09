"""
Application configuration.

Uses pydantic-settings. Defaults to SQLite for zero-setup runs.
To use PostgreSQL, set DATABASE_URL env var, e.g.:
    DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/diabetes_iot
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Diabetes IoT Recommender API"
    app_version: str = "1.0.0"
    database_url: str = "sqlite:///./diabetes_iot.db"
    log_level: str = "INFO"

    # Clinical reference ranges (non-diagnostic, used only for recommendation rules).
    # Values in mg/dL; aligned with common CGM "time in range" targets (70-180).
    tir_low: float = 70.0
    tir_high: float = 180.0
    severe_low: float = 54.0
    severe_high: float = 250.0

    # CORS
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]


settings = Settings()
