"""Telegram command handlers.

Every view that needs ranked data goes through `_ranked`, which caches per
chat. Preferences are per chat, so the cache has to be too — one reader's
security-only ranking must never be served to another reader who asked for
everything. Twelve HTTP fetches per keystroke would also be slow and rude
to the feeds.
"""
from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from src import pipeline
from src.bot import format as fmt
from src.bot.keyboards import CB_ALL, CB_CATEGORY, CB_DEPTH, settings_keyboard
from src.bot.preferences import store
from src.bot.state import state
from src.llm.digest import build_digest
from src.models import NewsItem
from src.scoring.categories import CATEGORY_IDS
from src.scoring.weights import weights_for

log = logging.getLogger(__name__)

_SEND = {"parse_mode": ParseMode.HTML, "disable_web_page_preview": True}


async def _ranked(update: Update, force: bool = False) -> list[NewsItem]:
    """Ranked items for this chat's preferences, re-running only when stale."""
    chat_id = update.effective_chat.id if update.effective_chat else "default"
    prefs = store.get(chat_id)

    if not force:
        cached = state.get_cached(chat_id, prefs)
        if cached is not None:
            return cached

    if update.effective_chat:
        await update.effective_chat.send_action(ChatAction.TYPING)

    result = await pipeline.run(
        enabled_categories=prefs.categories, depth=prefs.depth
    )
    state.remember(chat_id, prefs, result.items, result.market, result.stats)
    return result.items


# --- commands ---------------------------------------------------------

async def start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(fmt.render_help(), **_SEND)


async def top(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    limit = 5
    if ctx.args:
        try:
            limit = max(1, min(10, int(ctx.args[0])))
        except ValueError:
            await update.message.reply_text("Usage: /top [1-10]")
            return

    items = await _ranked(update)
    prefs = store.get(update.effective_chat.id)
    await update.message.reply_text(fmt.render_top(items, limit, prefs.depth), **_SEND)


async def digest(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat:
        await update.effective_chat.send_action(ChatAction.TYPING)

    chat_id = update.effective_chat.id
    prefs = store.get(chat_id)
    result = await pipeline.run(
        enabled_categories=prefs.categories, depth=prefs.depth
    )
    state.remember(chat_id, prefs, result.items, result.market, result.stats)

    built = await build_digest(result.items, result.market)
    await update.message.reply_text(fmt.render_digest(built, prefs.depth), **_SEND)


async def weights(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    prefs = store.get(update.effective_chat.id)
    await update.message.reply_text(
        fmt.render_settings(prefs, weights_for(prefs.depth)),
        reply_markup=settings_keyboard(prefs),
        **_SEND,
    )


async def why(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Not advertised in /help, but kept: it is how you audit a ranking."""
    if not ctx.args:
        await update.message.reply_text(
            "Usage: <code>/why 1</code> — the number from /top.", **_SEND
        )
        return
    try:
        index = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("Try <code>/why 1</code>.", **_SEND)
        return

    items = await _ranked(update)
    if not 1 <= index <= len(items):
        await update.message.reply_text(f"Pick a number between 1 and {len(items)}.")
        return
    await update.message.reply_text(fmt.render_why(items[index - 1], index), **_SEND)


# --- settings callbacks ----------------------------------------------

async def on_settings_button(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    prefs = store.get(chat_id)
    action, _, value = (query.data or "").partition(":")

    if action == CB_CATEGORY and value in CATEGORY_IDS:
        prefs.toggle(value)
    elif action == CB_DEPTH and value in ("data", "balanced", "analysis"):
        prefs.depth = value  # type: ignore[assignment]
    elif action == CB_ALL:
        prefs.categories = set(CATEGORY_IDS)
    else:
        return

    store.update(chat_id, prefs)
    # Preferences changed the formula, so anything cached was scored under
    # the old one and must not be served again.
    state.invalidate(chat_id)

    try:
        await query.edit_message_text(
            fmt.render_settings(prefs, weights_for(prefs.depth)),
            reply_markup=settings_keyboard(prefs),
            **_SEND,
        )
    except BadRequest as exc:
        # Telegram rejects an edit that produces identical content. That
        # happens on a double-tap and is not worth surfacing.
        if "not modified" not in str(exc).lower():
            raise


async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the traceback, tell the user something plain.

    Handlers reach the network on nearly every call, so failures are
    expected rather than exceptional. What must not happen is silence.
    """
    log.error("handler error", exc_info=ctx.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "Something broke on my side. It is logged — try again in a moment."
        )
