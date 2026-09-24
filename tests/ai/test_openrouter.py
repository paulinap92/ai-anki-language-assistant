from types import SimpleNamespace
from unittest.mock import Mock

from src.ai.providers.openrouter import OpenRouterVocabularyClient


def test_openrouter_uses_openai_compatible_base_url(monkeypatch):
    fake_client = Mock()
    constructor = Mock(return_value=fake_client)
    monkeypatch.setattr("src.ai.providers.openrouter.OpenAI", constructor)

    client = OpenRouterVocabularyClient(
        api_key="secret",
        model="openrouter/free",
        import_model="provider/free-import",
        review_model="provider/free-review",
    )

    constructor.assert_called_once_with(
        api_key="secret",
        base_url="https://openrouter.ai/api/v1",
    )
    assert client.provider_name == "OpenRouter"
    assert client.model_for_workflow("card") == "openrouter/free"
    assert client.model_for_workflow("import") == "provider/free-import"
    assert client.model_for_workflow("review") == "provider/free-review"


def test_openrouter_generation_reuses_existing_strict_provider_path(monkeypatch):
    fake_client = Mock()
    fake_client.responses.create.return_value = SimpleNamespace(
        output_text='{"ok": true}',
        usage=SimpleNamespace(input_tokens=4, output_tokens=3, total_tokens=7),
    )
    monkeypatch.setattr("src.ai.providers.openrouter.OpenAI", Mock(return_value=fake_client))
    client = OpenRouterVocabularyClient(api_key="secret", model="openrouter/free")

    result = client._generate_text("Return JSON")

    assert result == '{"ok": true}'
    fake_client.responses.create.assert_called_once_with(
        model="openrouter/free",
        input="Return JSON",
    )
    assert client._last_usage_metadata["total_tokens"] == 7
