"""Groq client using the existing OpenAI-compatible provider implementation."""

from openai import OpenAI

from src.ai.providers.openai_provider import OpenAiVocabularyClient


class GroqVocabularyClient(OpenAiVocabularyClient):
    """Generate language-learning content through Groq."""

    def __init__(
        self,
        api_key: str,
        model: str = "openai/gpt-oss-20b",
        *,
        import_model: str | None = None,
        review_model: str | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("GROQ_API_KEY is required for Groq.")
        self._client = OpenAI(
            api_key=api_key.strip(),
            base_url="https://api.groq.com/openai/v1",
        )
        self._model = model
        self._import_model = import_model or model
        self._review_model = review_model or import_model or model
        self._last_model = model
        self._last_workflow = "card"
        self._last_usage_metadata: dict[str, int] = {}

    @property
    def provider_name(self) -> str:
        """Return the provider name shown to the user."""
        return "Groq"
