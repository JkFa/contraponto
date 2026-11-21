"""LLM provider interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.ingest.material import Material
from app.models import Mode, Tone


class LLMError(Exception):
    """Provider failure carrying an API error code (LLM_FAILED, LLM_QUOTA, CONTENT_REFUSED)."""

    def __init__(self, code: str = "LLM_FAILED", detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


@dataclass
class GenerationContext:
    """Structured context for a call. Real providers only read the prompts; mock uses this."""

    task: Literal["script", "summarize"]
    mode: Mode = "react"
    tone: Tone = "analitico"
    duration_min: int = 5
    hosts: tuple[str, str] = ("Davi", "Lia")
    thesis: str | None = None
    focus_points: str | None = None
    primary: Material | None = None
    confronto: Material | None = None
    chunk_text: str = ""
    attempt: int = 0
    extra: dict[str, object] = field(default_factory=dict)


class LLMProvider(Protocol):
    name: str

    async def generate(self, system: str, user: str, ctx: GenerationContext) -> str:
        """Return the raw text (JSON for scripts) produced by the model."""
        ...
