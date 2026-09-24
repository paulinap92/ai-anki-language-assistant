from src.ai.factory import build_ai_clients
from src.core.config import get_settings


def _clear_provider_env(monkeypatch) -> None:
    for name in (
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "GROQ_API_KEY",
        "ANTHROPIC_API_KEY",
        "CLAUDE_API_KEY",
        "OLLAMA_MODEL",
        "AI_SETUP_MODE",
    ):
        monkeypatch.delenv(name, raising=False)


def test_get_settings_allows_first_run_without_ai_provider(monkeypatch) -> None:
    _clear_provider_env(monkeypatch)
    settings = get_settings()
    assert settings.setup_mode == "hybrid"


def test_local_profile_uses_ollama_and_ignores_cloud_keys(monkeypatch) -> None:
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("AI_SETUP_MODE", "local")
    monkeypatch.setenv("OLLAMA_MODEL", "gemma3:4b")
    monkeypatch.setenv("OPENAI_API_KEY", "should-not-be-used")

    settings = get_settings()
    clients = build_ai_clients(settings)

    assert settings.setup_mode == "local"
    assert list(clients) == ["Ollama Local (experimental)"]


def test_api_profile_does_not_activate_ollama(monkeypatch) -> None:
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("AI_SETUP_MODE", "api")
    monkeypatch.setenv("OLLAMA_MODEL", "gemma3:4b")

    settings = get_settings()
    clients = build_ai_clients(settings)

    assert settings.setup_mode == "api"
    assert clients == {}


def test_api_profile_can_activate_openrouter(monkeypatch) -> None:
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("AI_SETUP_MODE", "api")
    monkeypatch.setenv("OPENROUTER_API_KEY", "router-secret")
    monkeypatch.setenv("OPENROUTER_MODEL", "openrouter/free")

    settings = get_settings()
    clients = build_ai_clients(settings)

    assert settings.setup_mode == "api"
    assert "OpenRouter" in clients
