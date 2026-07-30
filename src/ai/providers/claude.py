"""Claude client for vocabulary flashcards and conversation practice."""

from __future__ import annotations

from anthropic import Anthropic

from src.ai.base import VocabularyAiClient
from src.ai.prompts import (
    build_conversation_feedback_prompt,
    build_conversation_start_prompt,
    build_grammar_analysis_prompt,
    build_batch_grammar_prompt,
    build_sentence_based_card_prompt,
    build_vocabulary_prompt,
)
from src.quality import normalize_lexical_value, validate_vocabulary_card
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
        self._last_usage_metadata: dict[str, int] = {}

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

        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0) if usage is not None else 0
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0) if usage is not None else 0
        self._last_usage_metadata = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        } if usage is not None else {}

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
        explanation_language: str,
        topic_context: str = "",
    ) -> VocabularyCard:
        """Generate a vocabulary flashcard with Claude."""
        raw_text = self._generate_text(
            build_vocabulary_prompt(
                word_or_phrase,
                target_language,
                explanation_language,
                topic_context,
            )
        )
        card = self._parse_card_response(raw_text, self.provider_name)
        warnings = validate_vocabulary_card(
            card,
            expected_input=word_or_phrase,
            expected_target_language=target_language,
            expected_explanation_language=explanation_language,
            topic_context=topic_context,
        )
        if warnings:
            card.quality_warnings = list(dict.fromkeys([*card.quality_warnings, *warnings]))

        if (
            card.is_valid
            and normalize_lexical_value(card.word_or_phrase)
            != normalize_lexical_value(word_or_phrase)
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

    def generate_grammar_card(
        self, grammar_item: str, target_language: str, topic_context: str = ""
    ) -> GrammarAnalysis:
        """Generate one Batch grammar card."""
        raw_text = self._generate_text(
            build_batch_grammar_prompt(grammar_item, target_language, topic_context)
        )
        return self._parse_grammar_analysis(raw_text, self.provider_name)

    def generate_sentence_card(
        self,
        raw_item: str,
        target_language: str,
        explanation_language: str,
        topic_context: str = "",
    ) -> VocabularyCard:
        """Generate one card from a user-provided example sentence."""
        raw_text = self._generate_text(
            build_sentence_based_card_prompt(raw_item, target_language, explanation_language, topic_context)
        )
        card = self._parse_card_response(raw_text, self.provider_name)
        warnings = validate_vocabulary_card(
            card,
            expected_input=card.word_or_phrase,
            expected_target_language=target_language,
            expected_explanation_language=explanation_language,
            topic_context=topic_context,
        )
        if warnings:
            card.quality_warnings = list(dict.fromkeys([*card.quality_warnings, *warnings]))
        return card

    def review_conversation_answer(
        self,
        topic: str,
        question: str,
        answer: str,
        target_language: str,
        improvement_level: str,
        feedback_language: str,
    ) -> ConversationFeedback:
        """Review an answer and continue the conversation with Claude."""
        raw_text = self._generate_text(
            build_conversation_feedback_prompt(
                topic,
                question,
                answer,
                target_language,
                improvement_level,
                feedback_language,
            )
        )
        return self._parse_conversation_feedback(raw_text, self.provider_name)
