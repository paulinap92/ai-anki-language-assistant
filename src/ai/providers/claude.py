"""Claude client for vocabulary flashcards and conversation practice."""

from __future__ import annotations

from anthropic import Anthropic

from src.ai.base import VocabularyAiClient
from src.ai.prompts import (
    build_conversation_feedback_prompt,
    build_conversation_start_prompt,
    build_grammar_analysis_prompt,
    build_vocabulary_prompt,
)
from src.domain.models import (
    ConversationFeedback,
    ConversationStart,
    GrammarAnalysis,
    VocabularyCard,
)


class ClaudeVocabularyClient(VocabularyAiClient):
    """Generate language-learning content using the Claude Messages API."""

    def __init__(self, api_key: str, model: str, max_tokens: int = 4096) -> None:
        """Initialize the Claude client.

        Args:
            api_key: Anthropic API key.
            model: Claude API model identifier.
            max_tokens: Maximum number of output tokens per response.
        """
        self._client = Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    @property
    def provider_name(self) -> str:
        """Return the provider name shown to the user."""
        return "Claude"

    def _generate_text(self, prompt: str) -> str:
        """Generate text for a prompt using Claude.

        Claude responses contain a list of content blocks. Only text blocks are
        joined; non-text blocks are ignored safely.
        """
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )

        text_parts = [
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text" and getattr(block, "text", None)
        ]
        return "".join(text_parts)

    def generate_card(
        self,
        word_or_phrase: str,
        target_language: str,
        explanation_language: str = "Polish",
    ) -> VocabularyCard:
        """Generate a vocabulary flashcard with Claude."""
        raw_text = self._generate_text(
            build_vocabulary_prompt(
                word_or_phrase,
                target_language,
                explanation_language,
            )
        )
        card = self._parse_card_response(raw_text, self.provider_name)

        if (
            card.is_valid
            and card.word_or_phrase.strip().casefold()
            != word_or_phrase.strip().casefold()
        ):
            raise ValueError(
                f"{self.provider_name} returned a different word or phrase: "
                f"{card.word_or_phrase!r} instead of {word_or_phrase!r}."
            )

        return card

    def start_conversation(
        self,
        topic: str,
        target_language: str,
    ) -> ConversationStart:
        """Generate the first conversation question with Claude."""
        raw_text = self._generate_text(
            build_conversation_start_prompt(topic, target_language)
        )
        return self._parse_conversation_start(raw_text, self.provider_name)

    def analyze_grammar(
        self,
        sentence: str,
        target_language: str,
    ) -> GrammarAnalysis:
        """Analyze one sentence and return a structured grammar explanation."""
        raw_text = self._generate_text(
            build_grammar_analysis_prompt(sentence, target_language)
        )
        return self._parse_grammar_analysis(raw_text, self.provider_name)

    def review_conversation_answer(
        self,
        topic: str,
        question: str,
        answer: str,
        target_language: str,
        improvement_level: str,
    ) -> ConversationFeedback:
        """Review an answer and continue the conversation with Claude."""
        raw_text = self._generate_text(
            build_conversation_feedback_prompt(
                topic,
                question,
                answer,
                target_language,
                improvement_level,
            )
        )
        return self._parse_conversation_feedback(raw_text, self.provider_name)
