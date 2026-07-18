"""Abstract interface and shared parsing for AI providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
import json
from typing import TypeVar

from pydantic import BaseModel

from src.domain.models import ConversationFeedback, ConversationStart, GrammarAnalysis, VocabularyCard


ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


class VocabularyAiClient(ABC):
    """Common interface for vocabulary and conversation AI providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return a user-facing provider name."""

    @abstractmethod
    def generate_card(
        self,
        word_or_phrase: str,
        target_language: str,
        explanation_language: str = "Polish",
        topic_context: str = "",
    ) -> VocabularyCard:
        """Generate one validated vocabulary flashcard."""

    @abstractmethod
    def start_conversation(self, topic: str, target_language: str) -> ConversationStart:
        """Generate the first conversation question for a learner-selected topic."""

    @abstractmethod
    def analyze_grammar(self, sentence: str, target_language: str) -> GrammarAnalysis:
        """Analyze the grammar and natural usage of one sentence."""

    @abstractmethod
    def review_conversation_answer(
        self,
        topic: str,
        question: str,
        answer: str,
        target_language: str,
        improvement_level: str,
    ) -> ConversationFeedback:
        """Provide feedback and the next question for one learner response."""

    @staticmethod
    def _parse_response(
        raw_text: str,
        provider_name: str,
        model_class: type[ResponseModel],
        response_description: str,
    ) -> ResponseModel:
        """Parse and validate JSON returned by an AI provider."""
        cleaned_text = raw_text.replace("```json", "").replace("```", "").strip()

        try:
            data = json.loads(cleaned_text)
            return model_class(**data)
        except Exception as exc:
            raise ValueError(
                f"{provider_name} returned invalid {response_description} data.\n"
                f"Raw response:\n{raw_text}"
            ) from exc

    @classmethod
    def _parse_card_response(cls, raw_text: str, provider_name: str) -> VocabularyCard:
        """Parse and validate a vocabulary flashcard response."""
        return cls._parse_response(raw_text, provider_name, VocabularyCard, "flashcard")

    @classmethod
    def _parse_conversation_start(
        cls, raw_text: str, provider_name: str
    ) -> ConversationStart:
        """Parse and validate an initial conversation question response."""
        return cls._parse_response(
            raw_text, provider_name, ConversationStart, "conversation question"
        )

    @classmethod
    def _parse_grammar_analysis(
        cls, raw_text: str, provider_name: str
    ) -> GrammarAnalysis:
        """Parse and validate a sentence-first grammar analysis response."""
        return cls._parse_response(
            raw_text, provider_name, GrammarAnalysis, "grammar analysis"
        )

    @classmethod
    def _parse_conversation_feedback(
        cls, raw_text: str, provider_name: str
    ) -> ConversationFeedback:
        """Parse and validate a conversation feedback response."""
        return cls._parse_response(
            raw_text, provider_name, ConversationFeedback, "conversation feedback"
        )
