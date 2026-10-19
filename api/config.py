from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database: defaults to zero-configuration local SQLite; overridden by DATABASE_URL env var (e.g. Postgres in Docker)
    database_url: str = "sqlite:///./statementiq.db"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+psycopg2://", 1)
            if v.startswith("postgresql://") and not v.startswith("postgresql+"):
                return v.replace("postgresql://", "postgresql+psycopg2://", 1)
        return v

    # Uploads
    upload_dir: Path = Path("./uploads")
    max_upload_mb: int = 10

    # Security
    statementiq_api_key: str | None = None

    # API URL
    api_url: str = "http://127.0.0.1:8001"

    # OCI Configuration
    oci_config_file: str = "~/.oci/config"
    oci_profile: str = "DEFAULT"
    oci_compartment_id: str | None = None
    oci_model_id: str | None = None


settings = Settings()


def get_settings() -> Settings:
    return settings
