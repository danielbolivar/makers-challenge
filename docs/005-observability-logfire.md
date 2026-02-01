# ADR 005: Observability (Logfire)

## Context

We need visibility into agent runs, tool calls, token usage, and application events (rate limits, memory summarization) for debugging and cost control.

## Decision

- **Tool:** Pydantic Logfire. When `LOGFIRE_TOKEN` is set in the environment, we enable it at startup in `main.py` and set the agent’s `instrument=True` so pydantic-ai sends spans (agent run, tool calls, token usage).
- **Application spans:** Custom spans or attributes for rate-limit hits (user_id, channel), memory summarization (user_id, conversation_id, duration), and RAG search (e.g. query length, top distance, guarded-or-not) can be added where needed. `user_id` and `conversation_id` are passed as metadata where available for correlation.

## Consequences

- With Logfire configured, traces appear in the Logfire dashboard. Without `LOGFIRE_TOKEN`, instrumentation is disabled and the app runs normally.
- No other observability backend is required; Logfire integrates with the pydantic-ai agent out of the box.
