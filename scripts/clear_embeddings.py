"""
Clear RAG embeddings: delete all rows from chunks and documents.
Use before re-ingesting to start from a clean state.
Usage: python -m scripts.clear_embeddings   (from project root)
"""

import asyncio
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from sqlalchemy import delete

from src.db import Chunk, Document, async_session_factory, init_db


async def main() -> None:
    await init_db()
    async with async_session_factory() as session:
        result_chunks = await session.execute(delete(Chunk))
        result_docs = await session.execute(delete(Document))
        await session.commit()
    print(f"Cleared {result_chunks.rowcount} chunks and {result_docs.rowcount} documents.")


if __name__ == "__main__":
    asyncio.run(main())
