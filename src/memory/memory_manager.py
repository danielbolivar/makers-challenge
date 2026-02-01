"""
Selective long-term memory: summarize expired conversation into User.profile_summary.
CRM-style: keep only biographical / business intent / preferences; discard ephemeral tech support.
"""

from google import genai
from google.genai import types

from src.config import settings

SYSTEM_PROMPT = """Act as an expert CRM Data Analyst. Your job is to update a client profile based on their latest conversation.

Inputs:
- Previous Profile: {current_summary}
- Recent Conversation: {new_messages}

Filtering rules:
1) EXTRACT (keep): Biographical data (Name, Job title, Company, Location). Business intent (Want to buy? Looking for API? Just curious?). Communication preferences (Formal? Technical? Direct?).
2) IGNORE (discard): Resolved technical support issues (bugs, load errors, UI questions). Empty greetings and goodbyes. One-off platform complaints.

Output: A single plain-text paragraph with the updated profile. If the conversation added no profile value (only ephemeral tech support), return the Previous Profile unchanged."""

SUMMARY_MODEL_FALLBACK = "gemini-1.5-flash"


def _format_messages(messages: list[dict]) -> str:
    """Format list of {role, content} into a single string for the prompt."""
    lines = []
    for m in messages:
        role = m.get("role", "unknown")
        content = m.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def summarize_conversation(current_summary: str, new_messages: list[dict]) -> str:
    """
    Update client profile from recent conversation using Gemini (temperature=0).
    Keeps only biographical / business / preference data; discards ephemeral tech support.
    If the conversation added no profile value, returns current_summary unchanged.
    """
    if not new_messages:
        return current_summary

    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    formatted = _format_messages(new_messages)

    prompt = SYSTEM_PROMPT.format(
        current_summary=current_summary or "(none)",
        new_messages=formatted,
    )

    config = types.GenerateContentConfig(
        temperature=0,
        max_output_tokens=1024,
    )

    for model_name in ("gemini-2.0-flash", "gemini-2.0-flash-001", SUMMARY_MODEL_FALLBACK):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            if response and response.text:
                return response.text.strip()
        except Exception:
            continue

    return current_summary
