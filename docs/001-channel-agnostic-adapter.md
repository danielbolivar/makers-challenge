# ADR 001: Channel-agnostic adapter

## Context

The chatbot must support multiple messaging channels (Telegram first, WhatsApp later) without duplicating agent or RAG logic.

## Decision

Channels are implemented as thin adapters that normalize incoming messages into a common contract:

- **Input:** `(user_id, channel_id, raw_message)` — external user id, channel identifier (e.g. `"telegram"`), and message text.
- **Output:** `(response_text, optional_attachments)` — reply to send back and optional media.

The agent, RAG, memory manager, and rate limiter live in `src/` and never import channel-specific libraries. The Telegram adapter in `src/telegram_bot.py` maps `Update` to `(user_id, "telegram", message_text)` and calls the shared `get_agent_response(session, user_id, channel_id, conversation_id, message_text)`.

## Consequences

- Adding WhatsApp (or another channel) requires a new adapter that implements the same contract and calls the same agent API.
- All business logic stays in one place; channels are I/O only.
