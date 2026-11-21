from __future__ import annotations

import json
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.ingest.material import Material
from app.jobs import JobManager
from app.main import create_app
from app.storage import Storage

PRIMARY_TEXT = (
    "O consumo de café cresceu trinta por cento no Brasil na última década. "
    "Segundo o autor, todo mundo que toma café vive mais. "
    "A pesquisa citada ouviu duzentas pessoas em uma única cidade. "
    "Por isso, o café deveria ser recomendado a todas as crianças."
)
CONFRONTO_TEXT = (
    "Dados oficiais mostram que o consumo de café cresceu doze por cento no período. "
    "Estudos de longo prazo não encontraram relação causal entre café e longevidade. "
    "Pediatras não recomendam cafeína para crianças."
)


def make_settings(tmp_path: Path, **over: Any) -> Settings:
    base: dict[str, Any] = dict(
        mock_llm=True,
        mock_tts=True,
        data_dir=tmp_path / "data",
        rate_limit_enabled=False,
        allowed_origins="http://localhost:5173,https://jkfa.github.io",
        public_base_url="http://testserver",
        llm_retry_delays=(0.0, 0.0),
        gemini_api_key="",
        groq_api_key="",
    )
    base.update(over)
    return Settings(_env_file=None, **base)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return make_settings(tmp_path)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


def wait_status(client: TestClient, eid: str, statuses: set[str], timeout: float = 20) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        ep = client.get(f"/api/episodes/{eid}").json()
        if ep["status"] in statuses:
            return ep
        time.sleep(0.05)
    raise AssertionError(f"timeout waiting {statuses}; last={ep['status']}")


def read_sse(client: TestClient, eid: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    with client.stream("GET", f"/api/episodes/{eid}/events") as resp:
        assert resp.headers["content-type"].startswith("text/event-stream")
        event = None
        for line in resp.iter_lines():
            if line.startswith("event: "):
                event = line[7:]
            elif line.startswith("data: ") and event:
                events.append((event, json.loads(line[6:])))
                if event in ("done", "error"):
                    break
    return events


def material(role: str, text: str, ts: bool = False) -> Material:
    import re

    sents = [s for s in re.split(r"(?<=[.!?])\s+", text) if s]
    return Material(
        role=role,  # type: ignore[arg-type]
        kind="youtube" if ts else "text",
        segments=[((i * 10) if ts else None, s) for i, s in enumerate(sents)],
    )


def manager_for(settings: Settings, **kw: Any) -> JobManager:
    return JobManager(settings, Storage(settings.data_dir), **kw)
