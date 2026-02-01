"""
Initialize the database: create pgvector extension and all tables.
Run after PostgreSQL is up (e.g. docker compose up -d).
Usage: python -m scripts.init_db   (from project root)
"""

import asyncio
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.database import init_db


async def main() -> None:
    await init_db()
    print("Database initialized: extension vector + tables (documents, chunks, users, chat_messages).")


if __name__ == "__main__":
    asyncio.run(main())
