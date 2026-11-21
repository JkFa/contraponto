"""Temporary on-disk storage with TTL."""

from __future__ import annotations

import shutil
import time
from pathlib import Path


class Storage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.episodes = root / "episodes"
        self.cache = root / "cache" / "youtube"
        self.episodes.mkdir(parents=True, exist_ok=True)
        self.cache.mkdir(parents=True, exist_ok=True)

    def episode_dir(self, episode_id: str) -> Path:
        path = self.episodes / episode_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def audio_path(self, episode_id: str) -> Path:
        return self.episodes / episode_id / "episode.mp3"

    def delete(self, episode_id: str) -> None:
        shutil.rmtree(self.episodes / episode_id, ignore_errors=True)

    def purge_cache(self, ttl_s: float) -> None:
        now = time.time()
        for path in self.cache.glob("*.json"):
            if now - path.stat().st_mtime > ttl_s:
                path.unlink(missing_ok=True)

    def purge_orphans(self, live_ids: set[str]) -> None:
        for path in self.episodes.iterdir():
            if path.is_dir() and path.name not in live_ids:
                shutil.rmtree(path, ignore_errors=True)
