"""Data shapes for the locked book.

Deliberately thin. There is no field here the engine can use to alter a
position -- no target price, no size, no re-rank hook. `Name.role` is
read, never written, by anything downstream of the loader.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Role = Literal["LONG", "SHORT"]


@dataclass(frozen=True)
class Sleeve:
    """The book's single microtheme, and its one shared kill-adjacent trigger."""

    id: str
    as_of: str
    locked: bool
    statement: str
    theme_watch: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Name:
    """One position. `thesis`, `kill` and `watch` are the only text the
    model is ever allowed to vote on -- it cannot write any of them."""

    ticker: str
    name: str
    aliases: list[str]
    market: str
    role: Role
    thesis: str
    kill: str
    watch: list[str] = field(default_factory=list)
    anchors: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Book:
    sleeve: Sleeve
    names: dict[str, Name]  # keyed by ticker, e.g. "0175.HK"

    @property
    def longs(self) -> list[Name]:
        return [n for n in self.names.values() if n.role == "LONG"]

    @property
    def shorts(self) -> list[Name]:
        return [n for n in self.names.values() if n.role == "SHORT"]
