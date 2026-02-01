"""
PostgreSQL async connection and table definitions.
Single source of truth: RAG chunks, chat history, users (long-term profile).
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Index, UniqueConstraint, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.settings import settings

from pgvector.sqlalchemy import Vector

# Embedding dimension; must be <= 2000 for pgvector HNSW index (text-embedding-004 with output_dimensionality=768)
VECTOR_DIM = 768


class Base(DeclarativeBase):
    """Declarative base for all models."""

    pass


class Document(Base):
    """Source document metadata (e.g. PDF) for re-ingest detection."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_path: Mapped[str] = mapped_column(nullable=False)
    checksum: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class Chunk(Base):
    """Text chunk with embedding for RAG similarity search."""

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int | None] = mapped_column(nullable=True)  # optional FK
    content: Mapped[str] = mapped_column(nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(VECTOR_DIM), nullable=False)
    metadata_json: Mapped[str | None] = mapped_column("metadata", nullable=True)  # e.g. page
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        Index(
            "chunks_embedding_hnsw_idx",
            embedding,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_l2_ops"},
        ),
    )


class User(Base):
    """User (per channel) for long-term profile summary. Updated lazily on conversation timeout."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(nullable=False, index=True)  # external id (e.g. Telegram)
    channel_id: Mapped[str] = mapped_column(nullable=False, index=True)
    profile_summary: Mapped[str] = mapped_column(default="", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "channel_id", name="uq_users_user_channel"),)


class ChatMessage(Base):
    """Single message in a conversation; supports timeout via conversation_id + created_at."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(nullable=False, index=True)
    channel_id: Mapped[str] = mapped_column(nullable=False, index=True)
    conversation_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    role: Mapped[str] = mapped_column(nullable=False)  # 'user' | 'assistant'
    content: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


def get_engine():
    """Create async engine with asyncpg. JIT off for compatibility."""
    return create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        connect_args={"server_settings": {"jit": "off"}},
    )


engine = get_engine()
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db():
    """Create extension and all tables. Call once at startup."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
