# ADR 006: Rate limiting

## Context

We must prevent API and cost spikes from a single user (or channel) spamming the bot.

## Decision

- **Placement:** Rate limiting is applied in the channel adapter (e.g. `src/telegram_bot.py`) before calling the agent. If the limit is exceeded, the adapter returns a fixed message (e.g. "Too many messages. Please wait a moment.") and does not call Gemini or RAG.
- **Scope:** Per `user_id`; optionally per `(user_id, channel_id)` via `src/rate_limit.py` (key = `user_id` or `user_id:channel_id`).
- **Algorithm:** Sliding window: at most `RATE_LIMIT_REQUESTS` (default 20) requests per `RATE_LIMIT_WINDOW_SECONDS` (default 60) per key. Implemented in-memory in `src/rate_limit.py` with a thread lock.
- **Multi-instance:** For multiple app instances, a Redis-backed store can be added and documented here; the same `check_and_record(user_id, channel_id)` API can be preserved.

## Consequences

- Single-process deployment is protected against spam without extra dependencies.
- Redis is optional for horizontal scaling; not required for the initial Telegram-only deployment.
