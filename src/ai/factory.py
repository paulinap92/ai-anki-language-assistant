"""Factory for configured vocabulary generation clients."""

from __future__ import annotations

from src.ai.base import VocabularyAiClient
from src.core.config import Settings
from src.ai.providers.gemini import GeminiVocabularyClient
from src.ai.providers.openai_provider import OpenAiVocabularyClient
from src.ai.providers.claude import ClaudeVocabularyClient
from src.ai.providers.ollama import OllamaVocabularyClient
from src.observability import configure_llmops, wrap_ai_client


def build_ai_clients(settings: Settings) -> dict[str, VocabularyAiClient]:
    """Create clients only for providers with configured API keys.

    Args:
        settings: Environment-backed application settings.

    Returns:
        Provider names mapped to initialized clients.
    """
    configure_llmops(
        enabled=settings.langsmith_tracing,
        project_name=settings.langsmith_project,
        api_key=settings.langsmith_api_key,
        endpoint=settings.langsmith_endpoint,
        redact_inputs=settings.langsmith_redact_inputs,
    )

    clients: dict[str, VocabularyAiClient] = {}

    if settings.gemini_api_key:
        client = GeminiVocabularyClient(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            import_model=settings.gemini_import_model,
            review_model=settings.gemini_review_model,
        )
        clients[client.provider_name] = client

    if settings.openai_api_key:
        client = OpenAiVocabularyClient(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            import_model=settings.openai_import_model,
            review_model=settings.openai_review_model,
        )
        clients[client.provider_name] = client

    if settings.anthropic_api_key:
        client = ClaudeVocabularyClient(
            api_key=settings.anthropic_api_key,
            model=settings.claude_model,
            import_model=settings.claude_import_model,
            review_model=settings.claude_review_model,
        )
        clients[client.provider_name] = client

    if settings.ollama_model:
        client = OllamaVocabularyClient(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )
        clients[client.provider_name] = client

    return {name: wrap_ai_client(client) for name, client in clients.items()}
