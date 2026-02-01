"""
Run-once ingest: read PDF from data/Coding case_v26.pdf, chunk by page,
embed with Gemini, insert into Postgres chunks (and optional documents).
Usage: python -m scripts.ingest  (from project root)
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import fitz  # pymupdf
from google import genai

from src.database import Chunk, Document, async_session_factory, init_db
from src.settings import settings

DEFAULT_PDF_PATH = _root / "data" / "Coding case_v26.pdf"
BATCH_SIZE = 10


def extract_chunks_from_pdf(pdf_path: Path) -> list[tuple[str, str]]:
    """Extract (content, metadata) per page. Metadata is e.g. 'page 1'."""
    doc = fitz.open(pdf_path)
    chunks = []
    for i in range(len(doc)):
        page = doc[i]
        text = page.get_text().strip()
        if not text:
            continue
        chunks.append((text, f"page {i + 1}"))
    doc.close()
    return chunks


def embed_batch(client: genai.Client, texts: list[str]) -> list[list[float]]:
    """Embed a list of texts with Gemini. Returns list of embedding vectors."""
    if not texts:
        return []
    result = client.models.embed_content(
        model=settings.EMBEDDING_MODEL,
        contents=texts,
    )
    if not result.embeddings:
        raise ValueError("Empty embeddings from API")
    return [list(emb.values) for emb in result.embeddings]


async def run_ingest(pdf_path: Path) -> None:
    """Create extension/tables, load PDF, embed, insert chunks."""
    await init_db()

    chunks_data = extract_chunks_from_pdf(pdf_path)
    if not chunks_data:
        print("No text extracted from PDF.")
        return

    client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    # Optional: upsert one document row for re-ingest detection
    doc_id = None
    async with async_session_factory() as session:
        doc = Document(source_path=str(pdf_path), checksum=None)
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        doc_id = doc.id

    # Batch embed and insert
    all_embeddings = []
    for i in range(0, len(chunks_data), BATCH_SIZE):
        batch = chunks_data[i : i + BATCH_SIZE]
        texts = [c[0] for c in batch]
        embeddings = embed_batch(client, texts)
        all_embeddings.extend(embeddings)

    # Insert chunks (we have embeddings in order)
    async with async_session_factory() as session:
        for (content, meta), embedding in zip(chunks_data, all_embeddings):
            chunk = Chunk(
                document_id=doc_id,
                content=content,
                embedding=embedding,
                metadata_json=meta,
            )
            session.add(chunk)
        await session.commit()

    print(f"Ingested {len(chunks_data)} chunks from {pdf_path}")


def main() -> None:
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF_PATH
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)
    asyncio.run(run_ingest(pdf_path))


if __name__ == "__main__":
    main()
