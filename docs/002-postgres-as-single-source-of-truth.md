# ADR 002: PostgreSQL as single source of truth

## Context

We need storage for (1) RAG vector embeddings and chunk metadata, and (2) user chat history and long-term profile. Using a single database simplifies operations and keeps data consistent.

## Decision

PostgreSQL 16 with the pgvector extension is the only persistent store:

- **RAG:** `documents` and `chunks` tables; embeddings in `chunks.embedding` (vector type); HNSW index for similarity search.
- **Chat:** `chat_messages` (user_id, channel_id, conversation_id, role, content, created_at) for short-term conversation context.
- **Users:** `users` (user_id, channel_id, profile_summary, updated_at) for long-term profile updated lazily on conversation timeout.

No separate vector DB (e.g. Pinecone, Weaviate) is used. All access is via SQLAlchemy 2.0 async (asyncpg).

## Consequences

- One connection pool, one backup, one migration story.
- Transactional consistency between chat history and user profile updates.
- pgvector supports approximate NN (HNSW) for scalable similarity search.
