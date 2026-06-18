"""Unit tests for the Claude provider without real API requests."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.ai.providers.claude import ClaudeVocabularyClient


@pytest.fixture
def mock_anthropic_client(monkeypatch):
    """Replace the real Anthropic client with a mock."""
    fake_client = Mock()
    monkeypatch.setattr(
        "src.ai.providers.claude.Anthropic",
        Mock(return_value=fake_client),
    )
    return fake_client


@pytest.fixture
def claude_client(mock_anthropic_client):
    """Create the application Claude client with fake credentials."""
    return ClaudeVocabularyClient(
        api_key="fake-api-key",
        model="claude-test-model",
        max_tokens=1234,
    )


def test_provider_name_returns_claude(claude_client):
    assert claude_client.provider_name == "Claude"


def test_generate_text_returns_joined_text_blocks(
    claude_client,
    mock_anthropic_client,
):
    mock_anthropic_client.messages.create.return_value = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="first "),
            SimpleNamespace(type="tool_use", text=None),
            SimpleNamespace(type="text", text="second"),
        ]
    )

    result = claude_client._generate_text("Test prompt")

    assert result == "first second"


def test_generate_text_calls_messages_api_with_expected_arguments(
    claude_client,
    mock_anthropic_client,
):
    mock_anthropic_client.messages.create.return_value = SimpleNamespace(content=[])

    claude_client._generate_text("Test prompt")

    mock_anthropic_client.messages.create.assert_called_once_with(
        model="claude-test-model",
        max_tokens=1234,
        messages=[{"role": "user", "content": "Test prompt"}],
    )


def test_generate_text_returns_empty_string_without_text_blocks(
    claude_client,
    mock_anthropic_client,
):
    mock_anthropic_client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(type="tool_use", text=None)]
    )

    assert claude_client._generate_text("Test prompt") == ""


def test_generate_card_rejects_changed_word(claude_client, monkeypatch):
    fake_card = Mock(is_valid=True, word_or_phrase="different phrase")
    monkeypatch.setattr(claude_client, "_generate_text", Mock(return_value="{}"))
    monkeypatch.setattr(
        claude_client,
        "_parse_card_response",
        Mock(return_value=fake_card),
    )

    with pytest.raises(ValueError, match="different word or phrase"):
        claude_client.generate_card("original phrase", "English", "Polish")
