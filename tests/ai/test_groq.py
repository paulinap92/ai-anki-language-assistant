from types import SimpleNamespace
from unittest.mock import Mock

from src.ai.providers.groq import GroqVocabularyClient


def test_groq_uses_openai_compatible_base_url(monkeypatch):
    fake_client = Mock()
    constructor = Mock(return_value=fake_client)
    monkeypatch.setattr("src.ai.providers.groq.OpenAI", constructor)

    client = GroqVocabularyClient(
        api_key="secret",
        model="openai/gpt-oss-20b",
        import_model="openai/gpt-oss-120b",
        review_model="openai/gpt-oss-120b",
    )

    constructor.assert_called_once_with(
        api_key="secret",
        base_url="https://api.groq.com/openai/v1",
    )
    assert client.provider_name == "Groq"
    assert client.model_for_workflow("card") == "openai/gpt-oss-20b"
    assert client.model_for_workflow("import") == "openai/gpt-oss-120b"
    assert client.model_for_workflow("review") == "openai/gpt-oss-120b"


def test_groq_generation_reuses_existing_responses_api_path(monkeypatch):
    fake_client = Mock()
    fake_client.responses.create.return_value = SimpleNamespace(
        output_text='{"ok": true}',
        usage=SimpleNamespace(input_tokens=5, output_tokens=4, total_tokens=9),
    )
    monkeypatch.setattr("src.ai.providers.groq.OpenAI", Mock(return_value=fake_client))
    client = GroqVocabularyClient(api_key="secret")

    result = client._generate_text("Return JSON")

    assert result == '{"ok": true}'
    fake_client.responses.create.assert_called_once_with(
        model="openai/gpt-oss-20b",
        input="Return JSON",
    )
    assert client._last_usage_metadata["total_tokens"] == 9
