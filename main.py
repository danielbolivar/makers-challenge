"""
Camaral RAG Chatbot — main entrypoint.
Loads settings, initializes Logfire (if configured), DB, and Telegram bot.
"""

import asyncio
import os
import sys

from src.database import init_db
from src.settings import settings
from src.telegram_bot import run_bot


def _init_logfire() -> None:
    """Initialize Logfire if LOGFIRE_TOKEN is set. Use LOGFIRE_BASE_URL for local/self-hosted backend."""
    if not settings.LOGFIRE_TOKEN:
        return
    try:
        import logfire
        if settings.LOGFIRE_BASE_URL:
            os.environ["LOGFIRE_BASE_URL"] = settings.LOGFIRE_BASE_URL.rstrip("/")
        logfire.configure(token=settings.LOGFIRE_TOKEN)
    except Exception as e:
        print(f"Logfire init skipped: {e}", file=sys.stderr)


async def main() -> None:
    """Initialize DB and run Telegram bot."""
    _init_logfire()
    await init_db()
    if not settings.TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN is not set.", file=sys.stderr)
        sys.exit(1)
    await run_bot(settings.TELEGRAM_BOT_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
