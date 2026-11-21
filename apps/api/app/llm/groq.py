"""Groq provider (OpenAI-compatible REST) used as fallback."""

from __future__ import annotations

import httpx

from app.llm._http import raise_for_status, with_retries
from app.llm.base import GenerationContext, LLMError

ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider:
    name = "groq"

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
        body: dict[str, object] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.6 if ctx.task == "script" else 0.2,
        }
        if ctx.task == "script":
            body["response_format"] = {"type": "json_object"}

        async def call() -> str:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(
                    ENDPOINT, headers={"Authorization": f"Bearer {self._key}"}, json=body
                )
            raise_for_status(resp)
            choices = resp.json().get("choices") or []
            if not choices:
                raise LLMError("LLM_FAILED", "no choices")
            text = (choices[0].get("message") or {}).get("content") or ""
            if not text.strip():
                raise LLMError("LLM_FAILED", "empty")
            return text

        return await with_retries(call, self.retry_delays)
