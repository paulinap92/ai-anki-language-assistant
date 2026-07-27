"""Optional LangSmith tracing and local LLMOps event logging.

This module is intentionally dependency-light: the desktop app must continue to
work when `langsmith` is not installed or when LANGSMITH_TRACING is disabled.
The wrapper records a small local event log for the UI tab and, when enabled,
sends redacted trace inputs/outputs to LangSmith.
"""

from __future__ import annotations

import os
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Deque

from pydantic import BaseModel

from src.ai.base import VocabularyAiClient
from src.domain.models import ConversationFeedback, ConversationStart, GrammarAnalysis, VocabularyCard


@dataclass
class LlmOpsEvent:
    """Small UI-friendly summary of one AI call."""

    timestamp: str
    feature: str
    provider: str
    model: str
    status: str
    latency_ms: int
    sent_to_langsmith: bool
    detail: str = ""
    trace_url: str = ""


class LlmOpsTracer:
    """Central optional tracer used by the GUI and AI-client wrappers."""

    def __init__(self) -> None:
        self.enabled: bool = False
        self.project_name: str = "ai-anki-language-assistant"
        self.redact_inputs: bool = True
        self.api_key_configured: bool = False
        self.langsmith_available: bool | None = None
        self.last_error: str = ""
        self._events: Deque[LlmOpsEvent] = deque(maxlen=80)

    def configure(
        self,
        *,
        enabled: bool,
        project_name: str = "ai-anki-language-assistant",
        api_key: str | None = None,
        endpoint: str | None = None,
        redact_inputs: bool = True,
    ) -> None:
        """Configure tracing from environment-backed settings."""
        self.enabled = bool(enabled)
        self.project_name = project_name or "ai-anki-language-assistant"
        self.redact_inputs = bool(redact_inputs)
        self.api_key_configured = bool(api_key or os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"))

        # LangSmith still supports LANGCHAIN_* aliases in many setups. Setting
        # both names makes the integration more forgiving without requiring the
        # user to know which SDK version is installed.
        if self.project_name:
            os.environ.setdefault("LANGSMITH_PROJECT", self.project_name)
            os.environ.setdefault("LANGCHAIN_PROJECT", self.project_name)
        if api_key:
            os.environ.setdefault("LANGSMITH_API_KEY", api_key)
            os.environ.setdefault("LANGCHAIN_API_KEY", api_key)
        if endpoint:
            os.environ.setdefault("LANGSMITH_ENDPOINT", endpoint)
            os.environ.setdefault("LANGCHAIN_ENDPOINT", endpoint)
        if self.enabled:
            os.environ.setdefault("LANGSMITH_TRACING", "true")
            os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        else:
            # Do not force-disable if the user deliberately set env vars outside
            # the app; just report our app-level setting as disabled.
            pass

        # Detect import lazily but store a human-readable status for the tab.
        self.langsmith_available = self._load_traceable() is not None
        if self.enabled and not self.langsmith_available:
            self.last_error = "Install langsmith package: pip install langsmith"
        elif self.enabled and not self.api_key_configured:
            self.last_error = "LANGSMITH_API_KEY is missing"
        else:
            self.last_error = ""

    def _load_traceable(self) -> Callable[..., Any] | None:
        try:
            from langsmith import traceable  # type: ignore

            return traceable
        except Exception:
            try:
                from langsmith.run_helpers import traceable  # type: ignore

                return traceable
            except Exception:
                return None

    def status_text(self) -> str:
        if not self.enabled:
            return "disabled"
        if not self.langsmith_available:
            return "enabled, but langsmith package is missing"
        if not self.api_key_configured:
            return "enabled, but API key is missing"
        return "enabled"

    def snapshot_events(self) -> list[LlmOpsEvent]:
        return list(self._events)

    def clear_events(self) -> None:
        self._events.clear()

    def _record_event(
        self,
        *,
        feature: str,
        provider: str,
        model: str,
        status: str,
        latency_ms: int,
        sent_to_langsmith: bool,
        detail: str = "",
    ) -> None:
        self._events.appendleft(
            LlmOpsEvent(
                timestamp=datetime.now().strftime("%H:%M:%S"),
                feature=feature,
                provider=provider,
                model=model,
                status=status,
                latency_ms=latency_ms,
                sent_to_langsmith=sent_to_langsmith,
                detail=detail[:500],
            )
        )

    def sanitize_value(self, value: Any) -> Any:
        """Return a JSON-ish value safe enough for external traces."""
        if isinstance(value, BaseModel):
            return self.output_summary(value)
        if isinstance(value, dict):
            return {str(k): self.sanitize_value(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.sanitize_value(v) for v in value[:20]]
        if isinstance(value, str):
            if self.redact_inputs:
                stripped = value.strip()
                return f"<redacted text len={len(stripped)} words={len(stripped.split())}>"
            return value[:2500]
        if value is None or isinstance(value, (bool, int, float)):
            return value
        return str(value)[:1000]

    def output_summary(self, value: Any) -> dict[str, Any] | str:
        """Return a compact, serializable output summary for traces."""
        if isinstance(value, VocabularyCard):
            return {
                "type": "VocabularyCard",
                "word_or_phrase": value.word_or_phrase,
                "target_language": value.target_language,
                "is_valid": value.is_valid,
                "quality_warnings_count": len(value.quality_warnings or []),
                "example_preview": (value.example or "")[:220],
            }
        if isinstance(value, GrammarAnalysis):
            return {
                "type": "GrammarAnalysis",
                "structure": value.structure,
                "target_language": value.target_language,
                "sentence_preview": (value.sentence or "")[:220],
            }
        if isinstance(value, ConversationStart):
            return {
                "type": "ConversationStart",
                "question_preview": (value.question or "")[:220],
            }
        if isinstance(value, ConversationFeedback):
            return {
                "type": "ConversationFeedback",
                "corrections_count": len(value.corrections or []),
                "suggestions_count": len(value.suggested_vocabulary or []),
                "next_question_preview": (value.next_question or "")[:220],
            }
        if isinstance(value, str):
            if self.redact_inputs:
                stripped = value.strip()
                return f"<redacted output len={len(stripped)} words={len(stripped.split())}>"
            return value[:2500]
        if isinstance(value, BaseModel):
            return {"type": value.__class__.__name__}
        return str(value)[:1000]

    def trace_call(
        self,
        *,
        feature: str,
        provider: str,
        model: str,
        inputs: dict[str, Any],
        metadata: dict[str, Any] | None,
        call_fn: Callable[[], Any],
    ) -> Any:
        """Run call_fn, optionally sending a LangSmith trace and always logging locally."""
        start = time.perf_counter()
        sent_to_langsmith = False
        traceable = self._load_traceable() if self.enabled else None
        can_send = bool(self.enabled and traceable and self.api_key_configured)
        safe_inputs = self.sanitize_value(inputs)
        safe_metadata = self.sanitize_value(metadata or {})

        if not can_send:
            try:
                result = call_fn()
            except Exception as exc:
                latency_ms = int((time.perf_counter() - start) * 1000)
                self._record_event(
                    feature=feature,
                    provider=provider,
                    model=model,
                    status="error",
                    latency_ms=latency_ms,
                    sent_to_langsmith=False,
                    detail=str(exc),
                )
                raise
            latency_ms = int((time.perf_counter() - start) * 1000)
            self._record_event(
                feature=feature,
                provider=provider,
                model=model,
                status="ok" if not self.enabled else "not_sent",
                latency_ms=latency_ms,
                sent_to_langsmith=False,
                detail=self.last_error if self.enabled else "LangSmith disabled; local event only.",
            )
            return result

        holder: dict[str, Any] = {}

        def _run_traced(safe_inputs_arg: dict[str, Any]) -> Any:
            result = call_fn()
            holder["result"] = result
            return self.output_summary(result)

        try:
            try:
                traced_fn = traceable(  # type: ignore[misc]
                    name=feature,
                    run_type="chain",
                    metadata=safe_metadata,
                    tags=["ai-anki", str(provider), str(feature)],
                )(_run_traced)
            except TypeError:
                # Older SDK fallback: fewer decorator kwargs.
                traced_fn = traceable(name=feature)(_run_traced)  # type: ignore[misc]
            traced_fn(safe_inputs)
            sent_to_langsmith = True
            result = holder.get("result")
            latency_ms = int((time.perf_counter() - start) * 1000)
            self._record_event(
                feature=feature,
                provider=provider,
                model=model,
                status="ok",
                latency_ms=latency_ms,
                sent_to_langsmith=True,
                detail=f"Sent to LangSmith project: {self.project_name}",
            )
            return result
        except Exception as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            self._record_event(
                feature=feature,
                provider=provider,
                model=model,
                status="error",
                latency_ms=latency_ms,
                sent_to_langsmith=sent_to_langsmith,
                detail=str(exc),
            )
            raise


TRACER = LlmOpsTracer()


def configure_llmops(
    *,
    enabled: bool,
    project_name: str,
    api_key: str | None = None,
    endpoint: str | None = None,
    redact_inputs: bool = True,
) -> None:
    TRACER.configure(
        enabled=enabled,
        project_name=project_name,
        api_key=api_key,
        endpoint=endpoint,
        redact_inputs=redact_inputs,
    )


def get_llmops_tracer() -> LlmOpsTracer:
    return TRACER


class TracedVocabularyAiClient(VocabularyAiClient):
    """VocabularyAiClient wrapper that adds optional LangSmith tracing."""

    def __init__(self, inner: VocabularyAiClient) -> None:
        self._inner = inner
        self._model = str(getattr(inner, "_model", ""))

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    @property
    def provider_name(self) -> str:
        return self._inner.provider_name

    def _trace(self, feature: str, inputs: dict[str, Any], call_fn: Callable[[], Any]) -> Any:
        metadata = {
            "feature": feature,
            "provider": self.provider_name,
            "model": self._model,
            "app": "AI Anki Language Assistant",
        }
        return TRACER.trace_call(
            feature=feature,
            provider=self.provider_name,
            model=self._model,
            inputs=inputs,
            metadata=metadata,
            call_fn=call_fn,
        )

    def _generate_text(self, prompt: str) -> str:
        generate_text = getattr(self._inner, "_generate_text")
        return self._trace(
            "raw_text_generation",
            {"prompt": prompt, "purpose": "direct prompt call"},
            lambda: generate_text(prompt),
        )

    def generate_card(
        self,
        word_or_phrase: str,
        target_language: str,
        explanation_language: str,
        topic_context: str = "",
    ) -> VocabularyCard:
        return self._trace(
            "vocabulary_card_generation",
            {
                "word_or_phrase": word_or_phrase,
                "target_language": target_language,
                "explanation_language": explanation_language,
                "topic_context": topic_context,
            },
            lambda: self._inner.generate_card(word_or_phrase, target_language, explanation_language, topic_context),
        )

    def start_conversation(self, topic: str, target_language: str) -> ConversationStart:
        return self._trace(
            "conversation_start",
            {"topic": topic, "target_language": target_language},
            lambda: self._inner.start_conversation(topic, target_language),
        )

    def analyze_grammar(self, sentence: str, target_language: str) -> GrammarAnalysis:
        return self._trace(
            "grammar_analysis",
            {"sentence": sentence, "target_language": target_language},
            lambda: self._inner.analyze_grammar(sentence, target_language),
        )

    def generate_grammar_card(
        self, grammar_item: str, target_language: str, topic_context: str = ""
    ) -> GrammarAnalysis:
        return self._trace(
            "grammar_card_generation",
            {"grammar_item": grammar_item, "target_language": target_language, "topic_context": topic_context},
            lambda: self._inner.generate_grammar_card(grammar_item, target_language, topic_context),
        )

    def generate_sentence_card(
        self,
        raw_item: str,
        target_language: str,
        explanation_language: str,
        topic_context: str = "",
    ) -> VocabularyCard:
        return self._trace(
            "provided_example_card_generation",
            {
                "raw_item": raw_item,
                "target_language": target_language,
                "explanation_language": explanation_language,
                "topic_context": topic_context,
            },
            lambda: self._inner.generate_sentence_card(raw_item, target_language, explanation_language, topic_context),
        )

    def review_conversation_answer(
        self,
        topic: str,
        question: str,
        answer: str,
        target_language: str,
        improvement_level: str,
        feedback_language: str,
    ) -> ConversationFeedback:
        return self._trace(
            "conversation_feedback",
            {
                "topic": topic,
                "question": question,
                "answer": answer,
                "target_language": target_language,
                "improvement_level": improvement_level,
                "feedback_language": feedback_language,
            },
            lambda: self._inner.review_conversation_answer(
                topic, question, answer, target_language, improvement_level, feedback_language
            ),
        )


def wrap_ai_client(client: VocabularyAiClient) -> VocabularyAiClient:
    if isinstance(client, TracedVocabularyAiClient):
        return client
    return TracedVocabularyAiClient(client)
