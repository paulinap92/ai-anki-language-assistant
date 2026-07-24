"""Local Ollama client for vocabulary flashcards and conversation practice."""

from __future__ import annotations

import json
from urllib import request, error

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


class OllamaVocabularyClient(VocabularyAiClient):
    """Generate language-learning content with a local Ollama model."""

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    @property
    def provider_name(self) -> str:
        return "Ollama Local (experimental)"

    def _local_model_prompt_wrapper(self, prompt: str) -> str:
        """Add strict guardrails for small/local models without changing app logic."""
        return f"""
LOCAL MODEL STRICT MODE:
- You are a small local model. Follow the requested JSON schema exactly.
- Return only valid JSON. No markdown, no comments, no extra text.
- Use only the requested target language for target-language fields.
- Use only the requested explanation/feedback language for explanation fields.
- Use the standard writing system/script for each requested language.
- Do not switch to another language or another script.
- Do not use Cyrillic unless the requested language normally uses Cyrillic.
- Keep wording simple, short, and deterministic.

USER TASK:
{prompt}
""".strip()

    def _generate_text(self, prompt: str) -> str:
        """Generate text using Ollama's local /api/generate endpoint."""
        prompt = self._local_model_prompt_wrapper(prompt)
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            # Ask Ollama to bias the model toward a JSON object. The app still
            # validates the final response with the same parser used by API providers.
            "format": "json",
            "options": {
                "temperature": 0.2,
            },
        }
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self._base_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=120) as response:
                raw = response.read().decode("utf-8")
        except error.URLError as exc:
            raise RuntimeError(
                "Ollama is not reachable. Start Ollama and check OLLAMA_BASE_URL "
                f"in .env. Current URL: {self._base_url}"
            ) from exc

        try:
            result = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Ollama returned invalid HTTP JSON:\n{raw}") from exc
        if result.get("error"):
            raise RuntimeError(f"Ollama error: {result['error']}")
        return str(result.get("response") or "").strip()

    def generate_card(
        self,
        word_or_phrase: str,
        target_language: str,
        explanation_language: str,
        topic_context: str = "",
    ) -> VocabularyCard:
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
        raw_text = self._generate_text(build_conversation_start_prompt(topic, target_language))
        return self._parse_conversation_start(raw_text, self.provider_name)

    def analyze_grammar(self, sentence: str, target_language: str) -> GrammarAnalysis:
        raw_text = self._generate_text(build_grammar_analysis_prompt(sentence, target_language))
        return self._parse_grammar_analysis(raw_text, self.provider_name)

    def generate_grammar_card(
        self, grammar_item: str, target_language: str, topic_context: str = ""
    ) -> GrammarAnalysis:
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
        raw_text = self._generate_text(
            build_conversation_feedback_prompt(
                topic, question, answer, target_language, improvement_level, feedback_language
            )
        )
        return self._parse_conversation_feedback(raw_text, self.provider_name)
