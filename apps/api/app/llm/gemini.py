"""Google Gemini (AI Studio) provider via REST."""

from __future__ import annotations

import httpx

from app.llm._http import raise_for_status, with_retries
from app.llm.base import GenerationContext, LLMError

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


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
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(
                    ENDPOINT.format(model=self.model),
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
