import os
from pathlib import Path
from functools import lru_cache
from typing import Dict, Any, List, Optional
import yaml
from pydantic_settings import BaseSettings
from pydantic import Field

def _find_base_dir() -> Path:
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "config" / "rules.yaml").exists():
            return parent
    if Path("/app/config/rules.yaml").exists():
        return Path("/app")
    return current.parent.parent.parent.parent


BASE_DIR = _find_base_dir()
CONFIG_DIR = BASE_DIR / "config"
RULES_FILE = CONFIG_DIR / "rules.yaml"


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    APP_NAME: str = "FDR-Sentinel"
    APP_VERSION: str = "1.0.0"
    SYNTHETIC_BANNER: str = "Synthetic demo data. No real bank or AICTE data."

    # Security & Auth
    SECRET_KEY: str = "dev_insecure_jwt_secret_key_sih2026_fdr_sentinel_0987654321"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    AES_MASTER_KEY_HEX: str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://sentinel_user:sentinel_pass@localhost:5432/fdr_sentinel",
        description="Primary database connection string"
    )
    TEST_DATABASE_URL: str = "sqlite:///./test_sentinel.db"

    # Redis & Storage
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "sentinel_minio_admin"
    MINIO_SECRET_KEY: str = "sentinel_minio_secret_key_2026"
    MINIO_BUCKET_NAME: str = "fdr-documents"
    MINIO_SECURE: bool = False

    # Email / SMTP (MailHog default)
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: str = "sentinel-noreply@aicte-india.org"
    EMAILS_FROM_NAME: str = "FDR-Sentinel Alerts"

    # ClamAV
    CLAMAV_ENABLED: bool = False
    CLAMAV_HOST: str = "localhost"
    CLAMAV_PORT: int = 3310

    # Demo Simulation Settings
    SYNTHETIC_DATASET_SEED: int = 42
    DEMO_CLOCK_OFFSET_DAYS: int = 0

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


@lru_cache()
def get_rules() -> Dict[str, Any]:
    if not RULES_FILE.exists():
        return {}
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
