"""
RAG: embed with Gemini, similarity search in Postgres, guarded result.
If top chunk distance is above threshold, prepend "No relevant passage found" and omit weak chunks.
"""

from google import genai
from google.genai import types
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db import Chunk, VECTOR_DIM

# L2 distance for pgvector (<=> operator)
GUARDED_MESSAGE = "No relevant passage found in the knowledge base."


def _get_embedding_client() -> genai.Client:
    return genai.Client(api_key=settings.GOOGLE_API_KEY)


def embed_text(text: str) -> list[float]:
    """Embed a single string with Gemini. Synchronous for use in sync ingest script."""
    client = _get_embedding_client()
    result = client.models.embed_content(
        model=settings.EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=VECTOR_DIM),
    )
    if not result.embeddings:
        raise ValueError("Empty embeddings from API")
    return list(result.embeddings[0].values)


async def embed_text_async(text: str) -> list[float]:
    """Embed a single string (async). Uses sync client; run in executor if needed for non-blocking."""
    return embed_text(text)


async def search(
    session: AsyncSession,
    query: str,
    *,
    top_k: int | None = None,
    similarity_threshold: float | None = None,
) -> str:
    """
    Embed query, run similarity search, return formatted string for the agent.
    If the top chunk's L2 distance is above similarity_threshold, prepend GUARDED_MESSAGE
    and omit all chunks (so the agent does not hallucinate from weak context).
    """
    top_k = top_k or settings.RAG_TOP_K
    similarity_threshold = similarity_threshold if similarity_threshold is not None else settings.RAG_SIMILARITY_THRESHOLD

    query_embedding = await embed_text_async(query)

    stmt = (
        select(Chunk.content, Chunk.metadata_json, Chunk.embedding.l2_distance(query_embedding).label("distance"))
        .order_by(Chunk.embedding.l2_distance(query_embedding))
        .limit(top_k)
    )
    result = await session.execute(stmt)
    rows = result.all()

    if not rows:
        return GUARDED_MESSAGE

    top_distance = float(rows[0].distance) if rows[0].distance is not None else float("inf")
    if top_distance > similarity_threshold:
        return GUARDED_MESSAGE

    parts = []
    for row in rows:
        dist = float(row.distance) if row.distance is not None else float("inf")
        if dist > similarity_threshold:
            continue
        content = row.content or ""
        meta = row.metadata_json or ""
        if meta:
            parts.append(f"[{meta}]\n{content}")
        else:
            parts.append(content)
    if not parts:
        return GUARDED_MESSAGE
    return "\n\n---\n\n".join(parts)
