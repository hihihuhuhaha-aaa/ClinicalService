from __future__ import annotations

from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

_CONFIG_PATH = Path(__file__).parent / "config.yaml"
_AI_CONFIG_PATH = Path(__file__).parent / "ai_config.yaml"

config: dict = yaml.safe_load(_CONFIG_PATH.read_text()) if _CONFIG_PATH.exists() else {}
ai_config: dict = yaml.safe_load(_AI_CONFIG_PATH.read_text()) if _AI_CONFIG_PATH.exists() else {}


def _get(section: str, key: str, default=None):
    return config.get(section, {}).get(key, default)


class Settings(BaseSettings):
    """Secrets and environment-specific values only. Non-secret config lives in YAML files."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "development"

    APP_NAME: str = _get("app", "name", "Neural-Symbolic Clinical API")
    APP_VERSION: str = _get("app", "version", "0.1.0")
    DEBUG: bool = _get("app", "debug", False)

    HOST: str = _get("server", "host", "0.0.0.0")
    PORT: int = _get("server", "port", 8000)

    # Secrets — must come from .env, not YAML
    DATABASE_URL: str
    LLM_API_KEY: str = "dummy"

    # Langfuse observability
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_BASE_URL: str = "https://cloud.langfuse.com"


settings = Settings()
