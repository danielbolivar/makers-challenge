# ADR 004: Agent and memory

## Context

The assistant must answer from the knowledge base (RAG), keep conversation context (short-term), and use long-term user profile when useful. We use pydantic-ai for the agent and a two-layer memory model.

## Decision

- **Agent:** PydanticAI agent with `google-gla:gemini-2.0-flash` (or configurable), one tool `search_knowledge_base(query)` that calls `rag.search(session, query)` and returns the guarded string. System prompt instructs the agent to answer only from search results and offer escalation when information is missing.
- **Short-term memory:** Last N messages (configurable `CHAT_HISTORY_LIMIT`) for the current `conversation_id` are loaded from `chat_messages`, converted to pydantic-ai `ModelMessage` format, and passed as `message_history` to `agent.run()`. After each run, the user message and assistant reply are appended to `chat_messages`.
- **Long-term memory:** `User.profile_summary` is loaded and injected as optional instructions (e.g. "Known user context: …"). It is updated lazily when a conversation expires (timeout) via `memory_manager.summarize_conversation`; see ADR 007.

## Consequences

- The agent always has recent conversation context and optional profile context.
- Persistence and history loading are in `src/agent.py`; the Telegram adapter only passes user_id, channel_id, conversation_id, and message text.
