"""
Unit tests for selective memory: summarize_conversation.
Case A: tech support only -> previous summary unchanged.
Case B: profile/sales -> updated profile (Name, Company, Interest).
"""

from unittest.mock import MagicMock, patch

import pytest

from src.memory_manager import _format_messages, summarize_conversation


def test_summarize_empty_messages_returns_current_summary():
    """Empty conversation -> return current summary unchanged."""
    current = "Name: Alice. Company: Acme."
    assert summarize_conversation(current, []) == current


def test_summarize_conversation_case_a_tech_support_unchanged():
    """
    Case A (tech support only): "Login button doesn't work" -> "Try clearing cache" -> "Thanks."
    Mock LLM to return previous profile unchanged (no profile value added).
    """
    current_summary = "Name: Bob. Company: Beta."
    new_messages = [
        {"role": "user", "content": "Hi, the login button doesn't work."},
        {"role": "assistant", "content": "Try clearing your browser cache."},
        {"role": "user", "content": "Done, thanks."},
    ]

    mock_response = MagicMock()
    mock_response.text = current_summary

    with patch("src.memory_manager.genai.Client") as MockClient:
        mock_models = MagicMock()
        mock_models.generate_content.return_value = mock_response
        MockClient.return_value.models = mock_models

        result = summarize_conversation(current_summary, new_messages)

    assert result == current_summary


def test_summarize_conversation_case_b_profile_updated():
    """
    Case B (profile/sales): Carlos from Inmobiliaria X, interested in avatars.
    Mock LLM to return updated profile with Name, Company, Interest.
    """
    current_summary = ""
    new_messages = [
        {
            "role": "user",
            "content": "Hi, I'm Carlos from Inmobiliaria X. I'm interested in using avatars for virtual tours.",
        },
    ]

    expected_profile = "Name: Carlos. Company: Inmobiliaria X. Interest: Avatars for virtual tours."
    mock_response = MagicMock()
    mock_response.text = expected_profile

    with patch("src.memory_manager.genai.Client") as MockClient:
        mock_models = MagicMock()
        mock_models.generate_content.return_value = mock_response
        MockClient.return_value.models = mock_models

        result = summarize_conversation(current_summary, new_messages)

    assert "Carlos" in result
    assert "Inmobiliaria" in result
    assert "avatar" in result.lower() or "Avatar" in result


def test_format_messages_internal():
    """_format_messages produces role: content lines."""
    out = _format_messages(
        [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello"}]
    )
    assert "user: Hi" in out
    assert "assistant: Hello" in out
