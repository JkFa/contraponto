"""Environment-driven settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULTS = {
    "gemini_model": "gemini-3.6-flash",
    "groq_model": "llama-3.3-70b-versatile",
    "voice_host_1": "pt-BR-AntonioNeural",
    "voice_host_2": "pt-BR-FranciscaNeural",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"), env_file_encoding="utf-8", extra="ignore"
    )

    gemini_api_key: str = ""
    gemini_model: str = _DEFAULTS["gemini_model"]
    groq_api_key: str = ""
    groq_model: str = _DEFAULTS["groq_model"]
    llm_provider: str = "gemini"

    tts_provider: str = "edge"
    voice_host_1: str = _DEFAULTS["voice_host_1"]
    voice_host_2: str = _DEFAULTS["voice_host_2"]

    mock_llm: bool = False
    mock_tts: bool = False

    allowed_origins: str = "http://localhost:5173"
    public_base_url: str = ""
    render_external_url: str = ""  # injected by Render; used when PUBLIC_BASE_URL is empty
    frontend_url: str = "https://jkfa.github.io/contraponto/"
    data_dir: Path = Path("./.data")
    episode_ttl_hours: int = 24
    max_concurrent_renders: int = 2

    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 10
    episodes_per_hour: int = 3

    llm_timeout_s: float = 90.0
    llm_retry_delays: tuple[float, ...] = (2.0, 6.0)

    @field_validator("gemini_model", "groq_model", "voice_host_1", "voice_host_2", mode="before")
    @classmethod
    def _empty_to_default(cls, value: object, info: object) -> object:
        if isinstance(value, str) and not value.strip():
            return _DEFAULTS[info.field_name]  # type: ignore[attr-defined]
        return value

    @field_validator("mock_llm", "mock_tts", "rate_limit_enabled", mode="before")
    @classmethod
    def _empty_bool(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return False
        return value

    @field_validator("public_base_url", mode="after")
    @classmethod
    def _strip_base(cls, value: str) -> str:
        return value.strip().rstrip("/")

    @property
    def base_url(self) -> str:
        """Public URL of this backend (share links, audio URLs)."""
        return (
            self.public_base_url or self.render_external_url.rstrip("/") or "http://localhost:8000"
        )

    @property
    def origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def llm_name(self) -> str:
        if self.mock_llm or self.llm_provider == "mock":
            return "mock"
        return self.llm_provider

    @property
    def tts_name(self) -> str:
        if self.mock_tts or self.tts_provider == "mock":
            return "mock"
        return self.tts_provider


@lru_cache
def get_settings() -> Settings:
    return Settings()
