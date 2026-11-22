from __future__ import annotations

import asyncio
import json

import httpx

from app.llm import gemini
from app.llm.base import GenerationContext


def test_pick_model_prefers_known_and_skips_previews() -> None:
    assert (
        gemini.pick_model(["models/gemini-3.8-flash", "models/gemini-3.6-flash"])
        == "gemini-3.6-flash"
    )
    assert (
        gemini.pick_model(["models/gemini-9.1-flash", "models/gemini-9.2-flash-preview"])
        == "gemini-9.1-flash"
    )
    assert (
        gemini.pick_model(["models/gemini-9.1-flash-lite", "models/gemini-9.1-flash"])
        == "gemini-9.1-flash"
    )
    assert gemini.pick_model(["models/text-embedding"]) is None


def test_discovers_model_on_404(monkeypatch) -> None:
    gemini._resolved.clear()
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-goog-api-key"] == "k"
        assert "key=" not in str(request.url)  # key never goes in the URL
        seen.append(request.url.path)
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "name": "models/gemini-3.6-flash",
                            "supportedGenerationMethods": ["generateContent"],
                        },
                        {
                            "name": "models/embedding-001",
                            "supportedGenerationMethods": ["embedContent"],
                        },
                    ]
                },
            )
        if "gemini-old" in request.url.path:
            return httpx.Response(404, json={"error": {"status": "NOT_FOUND"}})
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": json.dumps({"ok": 1})}]}}]}
        )

    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        gemini.httpx, "AsyncClient", lambda **kw: real_client(transport=transport, **kw)
    )
    provider = gemini.GeminiProvider("k", "gemini-old", retry_delays=(0.0,))
    out = asyncio.run(provider.generate("s", "u", GenerationContext(task="script")))
    assert json.loads(out) == {"ok": 1}
    assert seen == [
        "/v1beta/models/gemini-old:generateContent",
        "/v1beta/models",
        "/v1beta/models/gemini-3.6-flash:generateContent",
    ]
    # cached: next call goes straight to the discovered model
    seen.clear()
    asyncio.run(provider.generate("s", "u", GenerationContext(task="script")))
    assert seen == ["/v1beta/models/gemini-3.6-flash:generateContent"]
    gemini._resolved.clear()
