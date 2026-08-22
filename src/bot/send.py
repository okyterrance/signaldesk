"""Message delivery, with over-long content split rather than dropped.

Every outgoing view goes through here. Rendering decides what to say;
this decides how many messages that takes.
"""
from __future__ import annotations

from telegram.constants import ParseMode

from src.bot.format import split_messages

OPTS = {"parse_mode": ParseMode.HTML, "disable_web_page_preview": True}


async def reply(message, text: str, **kwargs) -> None:
    """Reply to a command, continuing into further messages if needed.

    Keyboards attach to the final part: a settings keyboard under part one
    of three would sit above the settings it controls.
    """
    parts = split_messages(text)
    for part in parts[:-1]:
        await message.reply_text(part, **OPTS)
    await message.reply_text(parts[-1], **OPTS, **kwargs)


async def push(bot, chat_id: str | int, text: str) -> None:
    """Send an unsolicited message (scheduled digest, threshold alert)."""
    for part in split_messages(text):
        await bot.send_message(chat_id=chat_id, text=part, **OPTS)
