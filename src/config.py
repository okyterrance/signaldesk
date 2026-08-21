"""Runtime settings, loaded from .env then environment.

Every secret is declared with `repr=False` so a stray traceback that dumps
the Settings object cannot leak a live key into logs or a terminal.
"""
from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Telegram ---
    telegram_bot_token: str = Field(default="", repr=False)
    telegram_chat_id: str = ""

    # --- LLM (TokenRouter, OpenAI-compatible proxy) ---
    tokenrouter_api_key: str = Field(default="", repr=False)
    tokenrouter_base_url: str = "https://api.tokenrouter.com/v1"
    # Ordered fallback chain. First provider to return usable output wins;
    # cross-family on purpose, so one vendor's outage is not ours.
    llm_model_chain: list[str] = ["anthropic/claude-sonnet-4.6", "openai/gpt-5.4"]
    llm_timeout_s: float = 60.0
    llm_max_tokens: int = 1400

    # --- Scheduling ---
    digest_time: str = "08:30"          # HH:MM in digest_tz
    digest_tz: str = "Asia/Hong_Kong"

    # --- Realtime alerts ---
    # A story at/above this score jumps the queue and is pushed on its own
    # rather than waiting for the next digest.
    alert_threshold: float = 0.72
    alert_poll_minutes: int = 15

    # --- News window / selection ---
    news_window_h: int = 24
    news_max_per_source: int = 40
    source_timeout_s: float = 12.0
    # Adaptive top-N per bucket: take everything above `select_threshold`,
    # capped at max_n; if that leaves fewer than min_n, backfill by rank.
    crypto_min_n: int = 4
    crypto_max_n: int = 8
    macro_min_n: int = 2
    macro_max_n: int = 4
    select_threshold: float = 0.30
    dedupe_threshold: float = 0.50

    @field_validator("llm_model_chain", mode="before")
    @classmethod
    def _split_chain(cls, v: object) -> object:
        """Accept a comma-separated string from .env as well as a list."""
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @field_validator("digest_time")
    @classmethod
    def _check_hhmm(cls, v: str) -> str:
        try:
            hh, mm = v.split(":")
            if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
                raise ValueError
        except (ValueError, AttributeError):
            raise ValueError(f"digest_time must be HH:MM, got {v!r}") from None
        return v

    def missing_required(self) -> list[str]:
        """Names of unset required keys, for a clear startup error."""
        required = {
            "TELEGRAM_BOT_TOKEN": self.telegram_bot_token,
            "TELEGRAM_CHAT_ID": self.telegram_chat_id,
            "TOKENROUTER_API_KEY": self.tokenrouter_api_key,
        }
        return [name for name, value in required.items() if not value]


settings = Settings()
