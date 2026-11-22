from __future__ import annotations

import asyncio

import httpx
import pytest

from app.llm._http import raise_for_status, with_retries
from app.llm.base import LLMError


def _resp(status: int, body: dict) -> httpx.Response:
    return httpx.Response(status, json=body, request=httpx.Request("POST", "https://x"))


def test_reason_is_reported_without_content() -> None:
    body = {
        "error": {
            "code": 400,
            "message": "API key not valid. secret prompt text here",
            "status": "INVALID_ARGUMENT",
            "details": [{"reason": "API_KEY_INVALID"}],
        }
    }
    with pytest.raises(LLMError) as exc:
        raise_for_status(_resp(400, body))
    assert exc.value.detail == "http 400 INVALID_ARGUMENT API_KEY_INVALID"
    assert "secret" not in exc.value.detail


def test_permanent_errors_are_not_retried() -> None:
    calls = {"n": 0}

    async def call() -> str:
        calls["n"] += 1
        raise_for_status(_resp(404, {"error": {"status": "NOT_FOUND"}}))
        return ""

    with pytest.raises(LLMError):
        asyncio.run(with_retries(call, (0.0, 0.0)))
    assert calls["n"] == 1


def test_transient_errors_are_retried() -> None:
    calls = {"n": 0}

    async def call() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise_for_status(_resp(503, {"error": {"status": "UNAVAILABLE"}}))
        return "ok"

    assert asyncio.run(with_retries(call, (0.0, 0.0))) == "ok"
    assert calls["n"] == 3
