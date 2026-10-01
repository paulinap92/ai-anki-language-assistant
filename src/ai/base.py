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
        explanation_language: str,
        topic_context: str = "",
    ) -> VocabularyCard:
        """Generate one validated vocabulary flashcard."""

    def generate_cards_batch(
        self,
        words_or_phrases: list[str],
        target_language: str,
        explanation_language: str,
        topic_context: str = "",
    ) -> list[VocabularyCard]:
        """Generate several vocabulary cards.

        Providers may override this to use one API request. The default keeps
        compatibility by falling back to one request per item.
        """
        return [
            self.generate_card(
                word_or_phrase,
                target_language,
                explanation_language,
                topic_context,
            )
            for word_or_phrase in words_or_phrases
        ]

    @abstractmethod
    def start_conversation(
        self,
        topic: str,
        target_language: str,
        flashcard_context: str = "",
    ) -> ConversationStart:
        """Generate the first question for a topic or flashcard-based conversation."""

    @abstractmethod
    def analyze_grammar(
        self,
        sentence: str,
        target_language: str,
        explanation_language: str = "Same as target",
    ) -> GrammarAnalysis:
        """Analyze the grammar and natural usage of one sentence."""

    @abstractmethod
    def generate_grammar_card(
        self,
        grammar_item: str,
        target_language: str,
        topic_context: str = "",
        explanation_language: str = "Same as target",
    ) -> GrammarAnalysis:
        """Generate one grammar card for a Batch grammar item."""

    @abstractmethod
    def generate_sentence_card(
        self,
        raw_item: str,
        target_language: str,
        explanation_language: str,
        topic_context: str = "",
    ) -> VocabularyCard:
        """Generate one card from a user-provided example sentence."""

    @abstractmethod
    def review_conversation_answer(
        self,
        topic: str,
        question: str,
        answer: str,
        target_language: str,
        improvement_level: str,
        feedback_language: str,
        flashcard_context: str = "",
        conversation_history: str = "",
    ) -> ConversationFeedback:
        """Provide feedback and continue a topic or flashcard-based conversation."""

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
        cls, raw_text: str, provider_name: str, target_language: str = "", explanation_language: str = ""
    ) -> GrammarAnalysis:
        """Parse the strict Grammar generation contract and adapt it to the existing app model.

        Grammar generation deliberately has a much smaller LLM contract than the
        legacy GrammarAnalysis model.  Downstream UI/Anki code remains unchanged.
        """
        cleaned_text = raw_text.replace("```json", "").replace("```", "").strip()
        try:
            data = json.loads(cleaned_text)
            required = {
                "target",
                "structure",
                "rule",
                "example",
                "explanation",
                "example_demonstrates_structure",
                "target_is_structure",
            }
            missing = sorted(required.difference(data))
            if missing:
                raise ValueError(f"missing Grammar fields: {', '.join(missing)}")

            if data["example_demonstrates_structure"] is not True:
                raise ValueError("Grammar example does not demonstrate the requested structure")
            if data["target_is_structure"] is not True:
                raise ValueError("Grammar target is not a concise grammar structure")

            target = str(data["target"]).strip()
            structure = str(data["structure"]).strip()
            rule = str(data["rule"]).strip()
            example = str(data["example"]).strip()
            explanation = str(data["explanation"]).strip()
            if not all((target, structure, rule, example, explanation)):
                raise ValueError("Grammar contract fields must not be empty")

            # Compatibility adapter only: keep the rest of v12.4.3+ untouched.
            return GrammarAnalysis(
                target=target,
                sentence=example,
                target_language=target_language,
                explanation_language=(
                    target_language
                    if not explanation_language or explanation_language == "Same as target"
                    else explanation_language
                ),
                meaning=rule,
                structure=structure,
                breakdown=[explanation],
                usage=rule,
                context_example=example,
                contrasts=[],
                common_mistakes=[],
                target_is_valid=True,
                example_demonstrates_target=True,
                validation_note="",
            )
        except Exception as exc:
            raise ValueError(
                f"{provider_name} returned invalid grammar analysis data.\n"
                f"Raw response:\n{raw_text}"
            ) from exc

    @classmethod
    def _parse_conversation_feedback(
        cls, raw_text: str, provider_name: str
    ) -> ConversationFeedback:
        """Parse and validate a conversation feedback response."""
        return cls._parse_response(
            raw_text, provider_name, ConversationFeedback, "conversation feedback"
        )
