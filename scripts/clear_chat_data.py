"""
Clear chat data: delete all chat_messages and users.
Use to test the agent as if starting a brand new conversation (no history, no profile).
Usage: python -m scripts.clear_chat_data   (from project root)
"""

import asyncio
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from sqlalchemy import delete

from src.db import ChatMessage, User, async_session_factory, init_db


async def main() -> None:
    await init_db()
    async with async_session_factory() as session:
        result_messages = await session.execute(delete(ChatMessage))
        result_users = await session.execute(delete(User))
        await session.commit()
    print(f"Cleared {result_messages.rowcount} chat messages and {result_users.rowcount} users. You can test as a fresh conversation.")


if __name__ == "__main__":
    asyncio.run(main())
