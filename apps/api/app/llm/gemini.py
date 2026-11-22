"""Google Gemini (AI Studio) provider via REST, with model auto-discovery on 404."""

from __future__ import annotations

import logging
import re

import httpx

from app.llm._http import raise_for_status, with_retries
from app.llm.base import GenerationContext, LLMError

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MODELS = "https://generativelanguage.googleapis.com/v1beta/models"
PREFERRED = (
    "gemini-3.6-flash",
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
)

log = logging.getLogger("contraponto.llm")
_resolved: dict[str, str] = {}  # configured model -> working model (process-wide cache)


def pick_model(available: list[str]) -> str | None:
    """Choose a Flash model: preferred list first, else the highest-versioned non-preview flash."""
    names = {a.removeprefix("models/") for a in available}
    for name in PREFERRED:
        if name in names:
            return name

    def version(n: str) -> tuple[float, int]:
        m = re.search(r"gemini-(\d+(?:\.\d+)?)", n)
        return (float(m.group(1)) if m else 0.0, 0 if "lite" in n else 1)

    flash = [
        n
        for n in names
        if "flash" in n
        and "preview" not in n
        and "exp" not in n
        and "image" not in n
        and "tts" not in n
        and "live" not in n
    ]
    return max(flash, key=version) if flash else None


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_s: float = 90.0,
        retry_delays: tuple[float, ...] = (2.0, 6.0),
    ) -> None:
        self._key = api_key
        self.model = model
        self.timeout_s = timeout_s
        self.retry_delays = retry_delays

    async def generate(self, system: str, user: str, ctx: GenerationContext) -> str:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0.6 if ctx.task == "script" else 0.2,
                "responseMimeType": "application/json" if ctx.task == "script" else "text/plain",
            },
        }

        async def call() -> str:
            model = _resolved.get(self.model, self.model)
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(
                    ENDPOINT.format(model=model),
                    headers={"x-goog-api-key": self._key},
                    json=body,
                )
                if resp.status_code == 404 and self.model not in _resolved:
                    found = await self._discover(client)
                    if found and found != model:
                        log.warning("gemini model=%s unavailable; using %s", model, found)
                        _resolved[self.model] = found
                        resp = await client.post(
                            ENDPOINT.format(model=found),
                            headers={"x-goog-api-key": self._key},
                            json=body,
                        )
            raise_for_status(resp)
            data = resp.json()
            if (data.get("promptFeedback") or {}).get("blockReason"):
                raise LLMError("CONTENT_REFUSED", "prompt blocked")
            candidates = data.get("candidates") or []
            if not candidates:
                raise LLMError("LLM_FAILED", "no candidates")
            cand = candidates[0]
            if cand.get("finishReason") in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST"):
                raise LLMError("CONTENT_REFUSED", cand.get("finishReason", ""))
            parts = (cand.get("content") or {}).get("parts") or []
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            if not text.strip():
                raise LLMError("LLM_FAILED", "empty")
            return text

        return await with_retries(call, self.retry_delays)

    async def _discover(self, client: httpx.AsyncClient) -> str | None:
        """List models this key can use (generateContent only) and pick a Flash one."""
        try:
            resp = await client.get(
                MODELS, headers={"x-goog-api-key": self._key}, params={"pageSize": 200}
            )
            if resp.status_code != 200:
                return None
            models = [
                m.get("name", "")
                for m in resp.json().get("models", [])
                if "generateContent" in (m.get("supportedGenerationMethods") or [])
            ]
        except (httpx.HTTPError, ValueError):
            return None
        return pick_model(models)
