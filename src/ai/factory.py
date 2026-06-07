"""Factory for configured vocabulary generation clients."""

from __future__ import annotations

from src.ai.base import VocabularyAiClient
from src.core.config import Settings
from src.ai.providers.gemini import GeminiVocabularyClient
from src.ai.providers.openai_provider import OpenAiVocabularyClient


def build_ai_clients(settings: Settings) -> dict[str, VocabularyAiClient]:
    """Create clients only for providers with configured API keys.

    Args:
        settings: Environment-backed application settings.

    Returns:
        Provider names mapped to initialized clients.
    """
    clients: dict[str, VocabularyAiClient] = {}

    if settings.gemini_api_key:
        client = GeminiVocabularyClient(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )
        clients[client.provider_name] = client

    if settings.openai_api_key:
        client = OpenAiVocabularyClient(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )
        clients[client.provider_name] = client

    return clients
