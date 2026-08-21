"""Find your TELEGRAM_CHAT_ID.

    1. Open Telegram, find the bot you made with @BotFather
    2. Send it any message (for a channel: add the bot as an admin, then
       post anything in the channel)
    3. Run:  python scripts/get_chat_id.py

Prints every chat the bot can currently see, with its id.
"""
from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
if not token:
    sys.exit("TELEGRAM_BOT_TOKEN is not set. Put it in .env first.")

response = httpx.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=20)
response.raise_for_status()
payload = response.json()

if not payload.get("ok"):
    sys.exit(f"Telegram rejected the token: {payload.get('description')}")

updates = payload.get("result") or []
if not updates:
    sys.exit(
        "No updates yet.\n"
        "Send your bot a direct message (or post in the channel it admins), "
        "then run this again within a few minutes."
    )

seen: dict[int, str] = {}
for update in updates:
    message = (
        update.get("message")
        or update.get("channel_post")
        or update.get("edited_message")
        or {}
    )
    chat = message.get("chat") or {}
    if chat.get("id") is None:
        continue
    label = chat.get("title") or chat.get("username") or chat.get("first_name") or "?"
    seen[chat["id"]] = f"{label}  ({chat.get('type')})"

if not seen:
    sys.exit("Got updates, but none carried a chat id. Try messaging the bot directly.")

print("\nChats this bot can see:\n")
for chat_id, label in seen.items():
    print(f"  TELEGRAM_CHAT_ID={chat_id}    # {label}")
print("\nCopy the line you want into your .env\n")
