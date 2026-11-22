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
            if exc.code == "CONTENT_REFUSED" or exc.detail.startswith(PERMANENT_PREFIXES):
                raise  # retrying will not fix a bad key, a bad request or an unknown model
            last = exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last = LLMError("LLM_FAILED", type(exc).__name__)
        if attempt < len(delays):
            await asyncio.sleep(delays[attempt])
    raise last


PERMANENT_PREFIXES = ("auth", "http 400", "http 404")


def _reason(resp: httpx.Response) -> str:
    """Machine-readable error reason from the provider (never prompt content or keys)."""
    try:
        err = resp.json().get("error") or {}
    except ValueError:
        return ""
    if not isinstance(err, dict):
        return ""
    bits = [str(err.get("status") or err.get("type") or err.get("code") or "")]
    for detail in err.get("details") or []:
        if isinstance(detail, dict) and detail.get("reason"):
            bits.append(str(detail["reason"]))
    return " ".join(b for b in bits if b)[:80]


def raise_for_status(resp: httpx.Response) -> None:
    if resp.status_code == 429:
        raise LLMError("LLM_QUOTA", f"429 {_reason(resp)}".strip())
    if resp.status_code in (401, 403):
        raise LLMError("LLM_FAILED", f"auth {resp.status_code} {_reason(resp)}".strip())
    if resp.status_code >= 400:
        raise LLMError("LLM_FAILED", f"http {resp.status_code} {_reason(resp)}".strip())
