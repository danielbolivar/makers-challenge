# ADR 003: RAG and chunking

## Context

We need to index a PDF (company knowledge) and retrieve relevant chunks for the agent. Quality and safety (no hallucination from weak matches) are important.

## Decision

- **Embedding model:** `gemini-embedding-001` or `text-embedding-004` (configurable via `EMBEDDING_MODEL`). Default 3072 dimensions; same model for ingest and query.
- **Chunking:** Page-based in ingest script (`scripts/ingest.py`); each page becomes one chunk with metadata `page N`.
- **Similarity:** L2 distance in pgvector (`<=>`); HNSW index for approximate nearest neighbor.
- **Top-k:** Configurable `RAG_TOP_K` (default 5).
- **Guarded RAG:** If the top chunk’s L2 distance is above `RAG_SIMILARITY_THRESHOLD`, the RAG layer returns only the message: *"No relevant passage found in the knowledge base."* and omits weak chunks so the agent does not hallucinate from low-quality context.

## Consequences

- Tuning `RAG_SIMILARITY_THRESHOLD` (e.g. 1.0) controls how strict retrieval is; higher threshold allows more distant matches.
- Page-based chunking is simple; future option: overlap or semantic chunking for finer granularity.
