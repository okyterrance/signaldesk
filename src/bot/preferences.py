"""Per-chat reader preferences, persisted to disk.

Preferences are keyed by chat id, not held globally. "Give the user
options" only means something if two readers can hold different ones, and
a bot that lands in a group should not let the last person to touch
/weights redefine everyone's digest.

The store is a single JSON file. A database would buy nothing here: the
data is a handful of fields per chat, written on a button press and read
once per pipeline run.
"""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from src.scoring.categories import CATEGORY_IDS

log = logging.getLogger(__name__)

Depth = Literal["data", "balanced", "analysis"]

DEPTH_LABELS: dict[str, str] = {
    "data": "Numbers",
    "balanced": "Balanced",
    "analysis": "Analysis",
}
DEPTH_BLURBS: dict[str, str] = {
    "data": "favour stories carrying hard figures",
    "balanced": "no preference either way",
    "analysis": "favour commentary, explainers and outlooks",
}

STORE_PATH = Path(__file__).resolve().parents[2] / "state.json"
_LOCK = threading.Lock()


@dataclass
class Prefs:
    """One reader's settings. Defaults are 'everything, no preference'."""

    categories: set[str] = field(default_factory=lambda: set(CATEGORY_IDS))
    depth: Depth = "balanced"

    def toggle(self, category: str) -> None:
        if category in self.categories:
            self.categories.discard(category)
        else:
            self.categories.add(category)

    def to_json(self) -> dict:
        return {"categories": sorted(self.categories), "depth": self.depth}

    @classmethod
    def from_json(cls, raw: dict) -> "Prefs":
        cats = {c for c in raw.get("categories", []) if c in CATEGORY_IDS}
        depth = raw.get("depth", "balanced")
        if depth not in DEPTH_LABELS:
            depth = "balanced"
        # An unreadable or empty category list falls back to everything
        # rather than to a silently empty digest.
        return cls(categories=cats or set(CATEGORY_IDS), depth=depth)  # type: ignore[arg-type]


class PreferenceStore:
    def __init__(self, path: Path = STORE_PATH) -> None:
        self.path = path
        self._cache: dict[str, Prefs] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text())
            self._cache = {
                chat: Prefs.from_json(value) for chat, value in raw.items()
            }
            log.info("loaded preferences for %s chat(s)", len(self._cache))
        except (json.JSONDecodeError, OSError, AttributeError) as exc:
            # A corrupt store must not stop the bot from starting; every
            # chat falls back to defaults, which is a working state.
            log.warning("could not read %s (%s); using defaults",
                        self.path.name, type(exc).__name__)
            self._cache = {}

    def _save(self) -> None:
        try:
            payload = {chat: p.to_json() for chat, p in self._cache.items()}
            tmp = self.path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(payload, indent=2))
            tmp.replace(self.path)   # atomic, so a crash mid-write cannot truncate
        except OSError as exc:
            log.warning("could not write %s (%s)", self.path.name, type(exc).__name__)

    def get(self, chat_id: str | int) -> Prefs:
        key = str(chat_id)
        with _LOCK:
            if key not in self._cache:
                self._cache[key] = Prefs()
            return self._cache[key]

    def update(self, chat_id: str | int, prefs: Prefs) -> None:
        with _LOCK:
            self._cache[str(chat_id)] = prefs
            self._save()


store = PreferenceStore()
