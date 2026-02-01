# ADR 007: Two-layer memory and selective summary

## Context

We want short-term conversation context for the agent and long-term user profile for personalization, without storing ephemeral tech-support chatter as profile.

## Decision

- **Layer 1 (short-term):** Last N messages of the current conversation, loaded from `chat_messages` and passed to the agent as `message_history`. No summarization; used as-is.
- **Layer 2 (long-term):** `User.profile_summary` — a single text field updated only when a conversation expires (timeout). Update is lazy: when the user sends a new message and the previous conversation is older than `CONVERSATION_TIMEOUT_SECONDS`, (1) load that conversation’s messages and the user’s current `profile_summary`, (2) call `memory_manager.summarize_conversation(current_summary, new_messages)` with Gemini (temperature=0), (3) write the result to `User.profile_summary`, (4) then start a new `conversation_id` for the new message.
- **Selective summarizer:** The summarizer prompt (in `src/memory_manager.py`) instructs the model to:
  - **Extract (keep):** Biographical data (name, job, company, location), business intent, communication preferences.
  - **Ignore (discard):** Resolved technical support issues, empty greetings/goodbyes, one-off platform complaints.
  - **Output:** A single plain-text paragraph. If the conversation added no profile value, return the previous profile unchanged.

## Consequences

- Profile stays relevant for sales/CRM use cases; tech-support noise is not persisted as profile.
- Lazy evaluation avoids summarizing on every message; only expired conversations trigger an LLM call for summarization.
- Test cases: (A) tech-support-only conversation → profile unchanged; (B) conversation with name/company/interest → profile updated (see `tests/test_memory_manager.py`).
