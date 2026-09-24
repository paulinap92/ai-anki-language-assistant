"""Factory for configured vocabulary generation clients."""

from __future__ import annotations

from src.ai.base import VocabularyAiClient
from src.core.config import Settings
from src.observability import configure_llmops, wrap_ai_client


def build_ai_clients(settings: Settings) -> dict[str, VocabularyAiClient]:
    """Create only AI clients allowed by the selected setup profile.

    Cloud SDK imports are intentionally lazy so a fully-local installation can
    run without OpenAI/Gemini/Claude packages installed.
    """
    configure_llmops(
        enabled=settings.langsmith_tracing,
        project_name=settings.langsmith_project,
        api_key=settings.langsmith_api_key,
        endpoint=settings.langsmith_endpoint,
        redact_inputs=settings.langsmith_redact_inputs,
    )

    clients: dict[str, VocabularyAiClient] = {}
    mode = (settings.setup_mode or "hybrid").casefold()
    allow_local = mode in {"local", "hybrid"}
    allow_cloud = mode in {"api", "hybrid"}

    if allow_cloud and settings.gemini_api_key:
        from src.ai.providers.gemini import GeminiVocabularyClient

        client = GeminiVocabularyClient(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            import_model=settings.gemini_import_model,
            review_model=settings.gemini_review_model,
        )
        clients[client.provider_name] = client

    if allow_cloud and settings.openrouter_api_key:
        from src.ai.providers.openrouter import OpenRouterVocabularyClient

        client = OpenRouterVocabularyClient(
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            import_model=settings.openrouter_import_model,
            review_model=settings.openrouter_review_model,
        )
        clients[client.provider_name] = client

    if allow_cloud and settings.groq_api_key:
        from src.ai.providers.groq import GroqVocabularyClient

        client = GroqVocabularyClient(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            import_model=settings.groq_import_model,
            review_model=settings.groq_review_model,
        )
        clients[client.provider_name] = client

    if allow_cloud and settings.openai_api_key:
        from src.ai.providers.openai_provider import OpenAiVocabularyClient

        client = OpenAiVocabularyClient(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            import_model=settings.openai_import_model,
            review_model=settings.openai_review_model,
        )
        clients[client.provider_name] = client

    if allow_cloud and settings.anthropic_api_key:
        from src.ai.providers.claude import ClaudeVocabularyClient

        client = ClaudeVocabularyClient(
            api_key=settings.anthropic_api_key,
            model=settings.claude_model,
            import_model=settings.claude_import_model,
            review_model=settings.claude_review_model,
        )
        clients[client.provider_name] = client

    if allow_local and settings.ollama_model:
        from src.ai.providers.ollama import OllamaVocabularyClient

        client = OllamaVocabularyClient(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )
        clients[client.provider_name] = client

    return {name: wrap_ai_client(client) for name, client in clients.items()}
