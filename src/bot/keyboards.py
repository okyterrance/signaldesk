"""Inline keyboards for the /weights settings screen.

Callback data is capped at 64 bytes by Telegram, so the payloads here are
short opaque codes (`cat:security`, `depth:data`) rather than anything
structured. The handler parses them back.
"""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.bot.preferences import DEPTH_LABELS, Prefs
from src.scoring.categories import CATEGORIES, CATEGORY_EMOJI

CB_CATEGORY = "cat"
CB_DEPTH = "depth"
CB_ALL = "all"


def settings_keyboard(prefs: Prefs) -> InlineKeyboardMarkup:
    """Five category toggles, three depth options, one reset.

    Categories get a row each: the labels are too long to pair up without
    truncating, and a mis-tap costs a round trip through the API.
    """
    rows = []

    for cid, label, _blurb, _pattern in CATEGORIES:
        state = "🟢" if cid in prefs.categories else "⚪️"
        rows.append([
            InlineKeyboardButton(
                f"{state}  {CATEGORY_EMOJI[cid]} {label}",
                callback_data=f"{CB_CATEGORY}:{cid}",
            )
        ])

    rows.append([
        InlineKeyboardButton(
            ("▸ " if prefs.depth == key else "") + DEPTH_LABELS[key],
            callback_data=f"{CB_DEPTH}:{key}",
        )
        for key in ("data", "balanced", "analysis")
    ])

    rows.append([
        InlineKeyboardButton("Select all categories", callback_data=f"{CB_ALL}:on")
    ])
    return InlineKeyboardMarkup(rows)
