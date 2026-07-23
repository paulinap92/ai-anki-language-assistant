"""OpenAI client for vocabulary flashcards and conversation practice."""

from openai import OpenAI

from src.ai.base import VocabularyAiClient
from src.domain.models import ConversationFeedback, ConversationStart, GrammarAnalysis, VocabularyCard
from src.quality import normalize_lexical_value, validate_vocabulary_card
from src.ai.prompts import (
    build_conversation_feedback_prompt,
    build_conversation_start_prompt,
    build_grammar_analysis_prompt,
    build_batch_grammar_prompt,
    build_sentence_based_card_prompt,
    build_vocabulary_prompt,
)


class OpenAiVocabularyClient(VocabularyAiClient):
    """Generate language-learning content using the OpenAI API."""

    def __init__(self, api_key: str, model: str) -> None:
        """Initialize the OpenAI client."""
        self._client = OpenAI(api_key=api_key)
        self._model = model

    @property
    def provider_name(self) -> str:
        """Return the provider name shown to the user."""
        return "OpenAI"

    def _generate_text(self, prompt: str) -> str:
        """Generate text for a prompt using the OpenAI Responses API."""
        response = self._client.responses.create(
            model=self._model,
            input=prompt,
        )
        return response.output_text or ""

    def generate_card(
        self,
        word_or_phrase: str,
        target_language: str,
        explanation_language: str,
        topic_context: str = "",
    ) -> VocabularyCard:
        """Generate a vocabulary flashcard with OpenAI."""
        raw_text = self._generate_text(
            build_vocabulary_prompt(word_or_phrase, target_language, explanation_language, topic_context)
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
        if card.is_valid and normalize_lexical_value(card.word_or_phrase) != normalize_lexical_value(word_or_phrase):
            raise ValueError(
                f"{self.provider_name} returned a different word or phrase: "
                f"{card.word_or_phrase!r} instead of {word_or_phrase!r}."
            )
        return card

    def start_conversation(self, topic: str, target_language: str) -> ConversationStart:
        """Generate the first conversation question with OpenAI."""
        raw_text = self._generate_text(build_conversation_start_prompt(topic, target_language))
        return self._parse_conversation_start(raw_text, self.provider_name)

    def analyze_grammar(self, sentence: str, target_language: str) -> GrammarAnalysis:
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
        """Review an answer and continue the conversation with OpenAI."""
        raw_text = self._generate_text(
            build_conversation_feedback_prompt(
                topic, question, answer, target_language, improvement_level, feedback_language
            )
        )
        return self._parse_conversation_feedback(raw_text, self.provider_name)
