"""Shared retry helper for HTTP LLM providers."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import httpx

from app.llm.base import LLMError


async def with_retries(
    call: Callable[[], Awaitable[str]], delays: tuple[float, ...] = (2.0, 6.0)
) -> str:
    """Run `call`, retrying transient failures (timeouts, 5xx, 429) with backoff."""
    last: LLMError = LLMError("LLM_FAILED", "no attempt")
    for attempt in range(len(delays) + 1):
        try:
            return await call()
        except LLMError as exc:
            if exc.code == "CONTENT_REFUSED":
                raise
            last = exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last = LLMError("LLM_FAILED", type(exc).__name__)
        if attempt < len(delays):
            await asyncio.sleep(delays[attempt])
    raise last


def raise_for_status(resp: httpx.Response) -> None:
    if resp.status_code == 429:
        raise LLMError("LLM_QUOTA", "429")
    if resp.status_code in (401, 403):
        raise LLMError("LLM_FAILED", f"auth {resp.status_code}")
    if resp.status_code >= 400:
        raise LLMError("LLM_FAILED", f"http {resp.status_code}")
