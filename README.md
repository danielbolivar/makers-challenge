# Camaral

RAG chatbot for customer service. Answers from a knowledge base (PDF) via Telegram. Built with Python, PostgreSQL (pgvector), Gemini, and pydantic-ai.

## Requirements

- Python 3.11+
- Docker (for PostgreSQL with pgvector)

## Setup

1. **Clone and enter the project**
   ```bash
   cd makers-challenge
   ```

2. **Virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Environment**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set at least:
   - `DATABASE_URL` (default works with Docker below)
   - `GOOGLE_API_KEY`
   - `TELEGRAM_BOT_TOKEN`

4. **Database**
   ```bash
   docker compose up -d
   python -m scripts.init_db
   ```

5. **Ingest PDF** (optional)
   ```bash
   python -m scripts.ingest data/camaral.pdf
   ```

6. **Run the bot**
   ```bash
   python main.py
   ```

## Commands

| Command | Description |
|--------|-------------|
| `python main.py` | Start the Telegram bot |
| `python -m scripts.init_db` | Create DB extension and tables |
| `python -m scripts.ingest [path.pdf]` | Ingest a PDF into the knowledge base |
| `python -m scripts.clear_embeddings` | Remove all chunks and documents |
| `python -m scripts.clear_chat_data` | Remove chat messages and users (fresh conversation) |

## Optional

- **Logfire:** Set `LOGFIRE_TOKEN` in `.env` for observability (omit `LOGFIRE_BASE_URL` to use cloud).
- **Tests:** `pytest` from the project root.
