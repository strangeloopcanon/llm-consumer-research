"""Application configuration and settings."""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Load settings from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="allow"
    )

    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: Optional[HttpUrl] = Field(default=None, alias="OPENAI_BASE_URL")
    openai_responses_model: str = Field(default="gpt-5", alias="RESEARCH_MODEL")
    openai_embedding_model: str = Field(default="text-embedding-3-small")

    max_concurrency: int = Field(default=64, ge=1, le=512)
    default_sample_size: int = Field(default=200, ge=1)

    anchor_bank_path: str = Field(default="src/ssr_service/data/anchors")
    persona_library_path: str = Field(default="src/ssr_service/data/personas")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    allow_provider_variants: bool = Field(default=False)
    provider_variant_share: float = Field(default=0.1, ge=0.0, le=0.5)
    provider_variants: List[str] = Field(default_factory=list)


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached settings instance."""

    return AppSettings()  # type: ignore[arg-type]


__all__ = ["AppSettings", "get_settings"]
