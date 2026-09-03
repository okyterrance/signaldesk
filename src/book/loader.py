"""Load and validate `config/book.yaml`.

Validation is strict on purpose. A book with three names, or a fifth name
someone forgot to give a `kill` condition, is not a smaller version of the
product -- it is a different, unreviewed thesis running live. Every rule
below raises rather than warns, because a book that loads with a hole in
it is worse than a book that refuses to load.
"""
from __future__ import annotations

import pathlib

import yaml

from src.book.models import Book, Name, Sleeve

DEFAULT_BOOK_PATH = (
    pathlib.Path(__file__).resolve().parents[2] / "config" / "book.yaml"
)

REQUIRED_NAME_FIELDS = ("name", "aliases", "market", "role", "thesis", "kill")
VALID_ROLES = {"LONG", "SHORT"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(f"book.yaml: {message}")


def load_book(path: pathlib.Path | str = DEFAULT_BOOK_PATH) -> Book:
    path = pathlib.Path(path)
    _require(path.exists(), f"no file at {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    sleeve_raw = raw.get("sleeve")
    _require(isinstance(sleeve_raw, dict), "missing top-level 'sleeve'")
    for field in ("id", "as_of", "locked", "statement"):
        _require(field in sleeve_raw, f"sleeve missing required field '{field}'")
    sleeve = Sleeve(
        id=str(sleeve_raw["id"]),
        as_of=str(sleeve_raw["as_of"]),
        locked=bool(sleeve_raw["locked"]),
        statement=str(sleeve_raw["statement"]).strip(),
        theme_watch=[str(w).strip() for w in (sleeve_raw.get("theme_watch") or [])],
    )
    _require(sleeve.locked, "sleeve.locked must be true -- this file is not a draft")

    names_raw = raw.get("names")
    _require(isinstance(names_raw, dict), "missing top-level 'names'")
    _require(
        len(names_raw) == 4,
        f"book must hold exactly 4 names, found {len(names_raw)}",
    )

    names: dict[str, Name] = {}
    for ticker, fields in names_raw.items():
        _require(isinstance(fields, dict), f"{ticker}: not a mapping")
        for req in REQUIRED_NAME_FIELDS:
            value = fields.get(req)
            _require(
                value not in (None, "", []),
                f"{ticker}: missing or empty required field '{req}'",
            )
        role = str(fields["role"]).strip().upper()
        _require(
            role in VALID_ROLES,
            f"{ticker}: role must be LONG or SHORT, got {fields['role']!r}",
        )
        aliases = fields["aliases"]
        _require(
            isinstance(aliases, list) and all(isinstance(a, str) for a in aliases),
            f"{ticker}: aliases must be a list of strings",
        )
        names[ticker] = Name(
            ticker=ticker,
            name=str(fields["name"]).strip(),
            aliases=aliases,
            market=str(fields["market"]).strip(),
            role=role,  # type: ignore[arg-type]
            thesis=str(fields["thesis"]).strip(),
            kill=str(fields["kill"]).strip(),
            watch=[str(w).strip() for w in (fields.get("watch") or [])],
            anchors=dict(fields.get("anchors") or {}),
        )

    longs = [n for n in names.values() if n.role == "LONG"]
    shorts = [n for n in names.values() if n.role == "SHORT"]
    _require(
        len(longs) == 2 and len(shorts) == 2,
        f"book must hold exactly 2 LONG and 2 SHORT, "
        f"found {len(longs)} LONG and {len(shorts)} SHORT",
    )

    return Book(sleeve=sleeve, names=names)
