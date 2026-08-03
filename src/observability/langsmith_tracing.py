"""Optional LangSmith tracing and local LLMOps event logging.

This module is intentionally dependency-light: the desktop app must continue to
work when `langsmith` is not installed or when LANGSMITH_TRACING is disabled.

The tracer has two jobs:

1. keep a local UI event log so the app can be debugged without any external
   service;
2. when enabled, send redacted LangSmith traces with quality metadata such as
   provider/model, prompt version, source workflow, latency, validation status,
   red flags, issue type and outcome.
"""

from __future__ import annotations

import math
import os
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Deque

from pydantic import BaseModel

from src.ai.base import VocabularyAiClient
from src.domain.models import ConversationFeedback, ConversationStart, GrammarAnalysis, VocabularyCard


@dataclass
class LlmOpsEvent:
    """Small UI-friendly summary of one AI/quality/outcome event."""

    timestamp: str
    feature: str
    provider: str
    model: str
    status: str
    latency_ms: int
    sent_to_langsmith: bool
    detail: str = ""
    trace_url: str = ""
    prompt_version: str = "unknown"
    source: str = "unknown"
    validation_passed: bool | None = None
    red_flags_count: int | None = None
    issue_type: str = ""
    outcome: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost: float | None = None
    cost_currency: str = "EUR"
    cost_source: str = ""


@dataclass
class QualitySnapshot:
    """Quality metadata extracted from a generated result or UI outcome."""

    validation_passed: bool | None = None
    red_flags_count: int | None = None
    issue_type: str = ""
    outcome: str = "generated"
    details: dict[str, Any] = field(default_factory=dict)

    def as_metadata(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "outcome": self.outcome,
            "issue_type": self.issue_type,
            **self.details,
        }
        if self.validation_passed is not None:
            data["validation_passed"] = self.validation_passed
        if self.red_flags_count is not None:
            data["red_flags_count"] = self.red_flags_count
        return {key: value for key, value in data.items() if value not in (None, "", [], {})}


FEATURE_DEFAULTS: dict[str, dict[str, str]] = {
    "raw_text_generation": {"prompt_version": "raw_prompt", "source": "internal_ai_call"},
    "vocabulary_card_generation": {"prompt_version": "vocab_prompt_v3", "source": "single_flashcard"},
    "batch_card_generation": {"prompt_version": "vocab_prompt_v3", "source": "batch_queue"},
    "provided_example_card_generation": {"prompt_version": "provided_example_prompt_v1", "source": "batch_provided_examples"},
    "grammar_analysis": {"prompt_version": "sentence_first_grammar_prompt_v1", "source": "grammar_tab"},
    "grammar_card_generation": {"prompt_version": "grammar_card_prompt_v1", "source": "batch_grammar"},
    "conversation_start": {"prompt_version": "conversation_start_prompt_v1", "source": "conversation_practice"},
    "conversation_feedback": {"prompt_version": "conversation_feedback_prompt_v2", "source": "conversation_practice"},
    "llmops_test_trace": {"prompt_version": "manual_test", "source": "llmops_tab"},
    "anki_outcome": {"prompt_version": "not_applicable", "source": "anki_connect"},
}


class LlmOpsTracer:
    """Central optional tracer used by the GUI and AI-client wrappers."""

    def __init__(self) -> None:
        self.enabled: bool = False
        self.project_name: str = "ai-anki-language-assistant"
        self.redact_inputs: bool = True
        self.api_key_configured: bool = False
        self.langsmith_available: bool | None = None
        self.last_error: str = ""
        self._events: Deque[LlmOpsEvent] = deque(maxlen=120)
        self.session_runs: int = 0
        self.session_total_tokens: int = 0
        self.session_estimated_cost: float = 0.0
        self.session_costed_runs: int = 0
        self.session_tts_cache_hits: int = 0

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

        # LangSmith still supports LANGCHAIN_* aliases in many setups.
        #
        # Important: do NOT use setdefault here. In a desktop session the process
        # may already contain stale values from a previous run, for example
        # LANGSMITH_TRACING=false or LANGCHAIN_PROJECT=anki-assistant. If we keep
        # those values, LangSmith's @traceable can silently become a no-op or send
        # runs to a different project while the UI says "sent". Configure the
        # exact project/API/tracing state every time settings are loaded.
        if self.project_name:
            os.environ["LANGSMITH_PROJECT"] = self.project_name
            os.environ["LANGCHAIN_PROJECT"] = self.project_name
        if api_key:
            os.environ["LANGSMITH_API_KEY"] = api_key
            os.environ["LANGCHAIN_API_KEY"] = api_key
        if endpoint:
            os.environ["LANGSMITH_ENDPOINT"] = endpoint
            os.environ["LANGCHAIN_ENDPOINT"] = endpoint
        tracing_value = "true" if self.enabled else "false"
        os.environ["LANGSMITH_TRACING"] = tracing_value
        os.environ["LANGCHAIN_TRACING_V2"] = tracing_value

        self.langsmith_available = self._load_traceable() is not None
        if self.enabled and not self.api_key_configured:
            self.last_error = "LangSmith configured but inactive: API key missing"
        elif self.enabled and not self.langsmith_available:
            self.last_error = "LangSmith configured but inactive: package missing. Install with: pip install langsmith"
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

    def _wait_for_tracers(self) -> None:
        """Flush LangSmith background tracers before reporting a run as sent.

        The LangSmith SDK may upload runs asynchronously. Without an explicit
        flush, the local UI could show "sent" while the run has not reached the
        LangSmith project page yet, especially for quick manual Test trace calls.
        This method is best-effort and must never break card generation.
        """
        wait_fn = None
        try:
            from langsmith import wait_for_all_tracers  # type: ignore

            wait_fn = wait_for_all_tracers
        except Exception:
            try:
                from langsmith.run_helpers import wait_for_all_tracers  # type: ignore

                wait_fn = wait_for_all_tracers
            except Exception:
                wait_fn = None

        if wait_fn is None:
            return

        try:
            wait_fn()
        except Exception:
            return

    def status_text(self) -> str:
        if not self.enabled:
            return "disabled"
        if not self.langsmith_available:
            return "configured but inactive: package missing"
        if not self.api_key_configured:
            return "configured but inactive: API key missing"
        return "enabled"

    def snapshot_events(self) -> list[LlmOpsEvent]:
        return list(self._events)

    def clear_events(self) -> None:
        self._events.clear()
        self.session_runs = 0
        self.session_total_tokens = 0
        self.session_estimated_cost = 0.0
        self.session_costed_runs = 0
        self.session_tts_cache_hits = 0

    def feature_defaults(self, feature: str) -> dict[str, str]:
        return dict(FEATURE_DEFAULTS.get(feature, {"prompt_version": "unknown", "source": "unknown"}))

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
        prompt_version: str = "unknown",
        source: str = "unknown",
        validation_passed: bool | None = None,
        red_flags_count: int | None = None,
        issue_type: str = "",
        outcome: str = "",
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        total_tokens: int | None = None,
        estimated_cost: float | None = None,
        cost_currency: str = "EUR",
        cost_source: str = "",
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
                detail=detail[:700],
                prompt_version=prompt_version,
                source=source,
                validation_passed=validation_passed,
                red_flags_count=red_flags_count,
                issue_type=issue_type,
                outcome=outcome,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                estimated_cost=estimated_cost,
                cost_currency=cost_currency,
                cost_source=cost_source,
            )
        )
        self.session_runs += 1
        if total_tokens:
            self.session_total_tokens += int(total_tokens)
        if estimated_cost is not None:
            self.session_estimated_cost += float(estimated_cost)
            self.session_costed_runs += 1
        if feature == "tts_generation" and "cache_hit=True" in str(detail):
            self.session_tts_cache_hits += 1

    def record_outcome(
        self,
        *,
        outcome: str,
        feature: str = "anki_outcome",
        provider: str = "system",
        model: str = "none",
        source: str = "anki_connect",
        prompt_version: str = "not_applicable",
        item: str = "",
        card_type: str = "",
        validation_passed: bool | None = None,
        red_flags_count: int | None = None,
        issue_type: str = "",
        detail: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a non-LLM user/outcome event in the local LLMOps log.

        This is intentionally local-only. It connects generated-card traces with
        human review outcomes such as added_to_anki, updated_existing_note or
        skipped, without requiring an external service.
        """
        bits = [f"outcome={outcome}"]
        if item:
            bits.append(f"item={item}")
        if card_type:
            bits.append(f"card_type={card_type}")
        if detail:
            bits.append(detail)
        self._record_event(
            feature=feature,
            provider=provider,
            model=model,
            status="ok",
            latency_ms=0,
            sent_to_langsmith=False,
            detail=" | ".join(bits),
            prompt_version=prompt_version,
            source=source,
            validation_passed=validation_passed,
            red_flags_count=red_flags_count,
            issue_type=issue_type,
            outcome=outcome,
            estimated_cost=(metadata or {}).get("estimated_cost"),
            cost_currency=str((metadata or {}).get("cost_currency") or (metadata or {}).get("estimated_cost_currency") or self._cost_currency()),
            cost_source=str((metadata or {}).get("cost_source") or ""),
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
            quality = self.quality_snapshot("vocabulary_card_generation", value).as_metadata()
            return {
                "type": "VocabularyCard",
                "word_or_phrase": value.word_or_phrase,
                "target_language": value.target_language,
                "is_valid": value.is_valid,
                "quality_warnings_count": len(value.quality_warnings or []),
                "example_preview": (value.example or "")[:220],
                "quality": quality,
            }
        if isinstance(value, GrammarAnalysis):
            quality = self.quality_snapshot("grammar_card_generation", value).as_metadata()
            return {
                "type": "GrammarAnalysis",
                "structure": value.structure,
                "target_language": value.target_language,
                "sentence_preview": (value.sentence or "")[:220],
                "quality": quality,
            }
        if isinstance(value, ConversationStart):
            return {
                "type": "ConversationStart",
                "question_preview": (value.question or "")[:220],
                "quality": self.quality_snapshot("conversation_start", value).as_metadata(),
            }
        if isinstance(value, ConversationFeedback):
            return {
                "type": "ConversationFeedback",
                "corrections_count": len(value.corrections or []),
                "suggestions_count": len(value.suggested_vocabulary or []),
                "next_question_preview": (value.next_question or "")[:220],
                "quality": self.quality_snapshot("conversation_feedback", value).as_metadata(),
            }
        if isinstance(value, str):
            if self.redact_inputs:
                stripped = value.strip()
                return f"<redacted output len={len(stripped)} words={len(stripped.split())}>"
            return value[:2500]
        if isinstance(value, BaseModel):
            return {"type": value.__class__.__name__}
        return str(value)[:1000]

    def quality_snapshot(self, feature: str, result: Any) -> QualitySnapshot:
        """Extract quality/outcome metrics from a generated result."""
        if isinstance(result, VocabularyCard):
            warnings = list(result.quality_warnings or [])
            hard_warnings = [warning for warning in warnings if str(warning).upper().startswith("HARD")]
            issues = self._issue_types_from_text([*warnings, result.validation_error, result.topic_warning])
            if not result.is_valid:
                issue_type = "invalid_input" if not issues else ",".join(_dedupe(["invalid_input", *issues]))
                return QualitySnapshot(
                    validation_passed=False,
                    red_flags_count=max(1, len(warnings) + (1 if result.validation_error else 0)),
                    issue_type=issue_type,
                    outcome="invalid_input",
                    details={
                        "card_type": "vocabulary",
                        "target_language": result.target_language,
                        "topic_fit": result.topic_fit,
                        "has_suggested_correction": bool(result.suggested_correction),
                    },
                )
            red_flags_count = len(warnings)
            validation_passed = not hard_warnings and red_flags_count == 0
            outcome = "generated" if validation_passed else "generated_with_warnings"
            return QualitySnapshot(
                validation_passed=validation_passed,
                red_flags_count=red_flags_count,
                issue_type=",".join(issues),
                outcome=outcome,
                details={
                    "card_type": "vocabulary",
                    "target_language": result.target_language,
                    "topic_fit": result.topic_fit,
                    "hard_warnings_count": len(hard_warnings),
                    "example_uses_target": result.example_uses_target,
                    "collocation_naturalness": result.collocation_naturalness,
                    "translation_naturalness": result.translation_naturalness,
                },
            )

        if isinstance(result, GrammarAnalysis):
            issues: list[str] = []
            missing = [
                name
                for name, value in {
                    "sentence": result.sentence,
                    "structure": result.structure,
                    "meaning": result.meaning,
                    "usage": result.usage,
                }.items()
                if not str(value or "").strip()
            ]
            if missing:
                issues.append("missing_required_field")
            # Guard against the exact class of bug we saw earlier: a grammar card
            # with a visible source sentence and a separate competing context
            # sentence. This is a warning, not an auto-blocker.
            sentence = str(result.sentence or "").strip()
            context = str(result.context_example or "").strip()
            if sentence and context and sentence not in context and context not in sentence:
                issues.append("possible_sentence_context_mismatch")
            validation_passed = not issues
            return QualitySnapshot(
                validation_passed=validation_passed,
                red_flags_count=len(issues),
                issue_type=",".join(_dedupe(issues)),
                outcome="generated" if validation_passed else "generated_with_warnings",
                details={
                    "card_type": "grammar",
                    "target_language": result.target_language,
                    "breakdown_count": len(result.breakdown or []),
                    "contrasts_count": len(result.contrasts or []),
                    "common_mistakes_count": len(result.common_mistakes or []),
                },
            )

        if isinstance(result, ConversationFeedback):
            return QualitySnapshot(
                validation_passed=True,
                red_flags_count=0,
                issue_type="",
                outcome="generated",
                details={
                    "card_type": "conversation_feedback",
                    "corrections_count": len(result.corrections or []),
                    "suggestions_count": len(result.suggested_vocabulary or []),
                    "has_mini_practice": bool(result.mini_practice),
                },
            )

        if isinstance(result, ConversationStart):
            has_question = bool(str(result.question or "").strip())
            return QualitySnapshot(
                validation_passed=has_question,
                red_flags_count=0 if has_question else 1,
                issue_type="" if has_question else "missing_required_field",
                outcome="generated" if has_question else "generated_with_warnings",
                details={"card_type": "conversation_start"},
            )

        return QualitySnapshot(validation_passed=None, red_flags_count=None, outcome="generated")

    def _issue_types_from_text(self, values: list[Any]) -> list[str]:
        text = "\n".join(str(value or "") for value in values).casefold()
        issues: list[str] = []
        if not text.strip():
            return issues
        if "input phrase changed" in text or "exact" in text and "input" in text:
            issues.append("exact_input_changed")
        if "example does not use" in text or "target item" in text or "target word" in text:
            issues.append("example_target_mismatch")
        if "translation" in text:
            issues.append("translation_issue")
        if "topic" in text:
            issues.append("topic_mismatch")
        if "language" in text:
            issues.append("language_mismatch")
        if "required field" in text or "empty" in text:
            issues.append("missing_required_field")
        if "natural" in text or "forced" in text or "collocation" in text:
            issues.append("naturalness_issue")
        if "source focus" in text:
            issues.append("wrong_source_focus")
        if "audio" in text:
            issues.append("audio_sentence_mismatch")
        return _dedupe(issues)


    def _env_float(self, name: str) -> float | None:
        value = os.getenv(name)
        if value is None:
            return None
        try:
            cleaned = value.strip().replace(",", ".")
            if not cleaned:
                return None
            return float(cleaned)
        except Exception:
            return None

    def _cost_currency(self) -> str:
        return (os.getenv("LLMOPS_COST_CURRENCY") or "EUR").strip() or "EUR"

    def _provider_key(self, provider: str) -> str:
        name = str(provider or "").casefold()
        if "openai" in name or "chatgpt" in name:
            return "OPENAI"
        if "gemini" in name or "google" in name:
            return "GEMINI"
        if "claude" in name or "anthropic" in name:
            return "CLAUDE"
        if "eleven" in name:
            return "ELEVENLABS"
        return "UNKNOWN"

    def _langsmith_provider_name(self, provider: str) -> str:
        key = self._provider_key(provider)
        return {
            "OPENAI": "openai",
            "GEMINI": "google_genai",
            "CLAUDE": "anthropic",
            "ELEVENLABS": "elevenlabs",
        }.get(key, str(provider or "unknown").lower())

    def _text_token_estimate(self, value: Any) -> int:
        """Very rough fallback: enough for local/session estimates when APIs do not return usage."""
        if value is None:
            return 0
        if isinstance(value, BaseModel):
            text = value.model_dump_json()
        elif isinstance(value, dict):
            text = " ".join(str(v) for v in value.values())
        elif isinstance(value, (list, tuple, set)):
            text = " ".join(str(v) for v in value)
        else:
            text = str(value)
        return max(0, math.ceil(len(text) / 4))

    def _normalize_usage_metadata(self, usage: Any) -> dict[str, int]:
        if not usage:
            return {}
        if not isinstance(usage, dict):
            data = {
                "input_tokens": getattr(usage, "input_tokens", None) or getattr(usage, "prompt_tokens", None) or getattr(usage, "prompt_token_count", None),
                "output_tokens": getattr(usage, "output_tokens", None) or getattr(usage, "completion_tokens", None) or getattr(usage, "candidates_token_count", None),
                "total_tokens": getattr(usage, "total_tokens", None) or getattr(usage, "total_token_count", None),
            }
        else:
            data = dict(usage)
        input_tokens = data.get("input_tokens") or data.get("prompt_tokens") or data.get("prompt_token_count") or 0
        output_tokens = data.get("output_tokens") or data.get("completion_tokens") or data.get("candidates_token_count") or 0
        total_tokens = data.get("total_tokens") or data.get("total_token_count") or (int(input_tokens or 0) + int(output_tokens or 0))
        result = {
            "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0),
            "total_tokens": int(total_tokens or 0),
        }
        return {key: value for key, value in result.items() if value > 0}

    def _cost_metadata_for_call(
        self,
        *,
        provider: str,
        model: str,
        inputs: dict[str, Any],
        result: Any,
        usage_metadata: Any = None,
    ) -> dict[str, Any]:
        usage = self._normalize_usage_metadata(usage_metadata)
        cost_source = "provider_usage" if usage else "estimated_from_text_length"
        if not usage:
            input_tokens = self._text_token_estimate(inputs)
            output_tokens = self._text_token_estimate(result)
            usage = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            }
        provider_key = self._provider_key(provider)
        input_rate = self._env_float(f"{provider_key}_INPUT_COST_PER_1M_TOKENS")
        output_rate = self._env_float(f"{provider_key}_OUTPUT_COST_PER_1M_TOKENS")
        estimated_cost = None
        if input_rate is not None or output_rate is not None:
            estimated_cost = (
                usage.get("input_tokens", 0) * float(input_rate or 0.0)
                + usage.get("output_tokens", 0) * float(output_rate or 0.0)
            ) / 1_000_000
        metadata: dict[str, Any] = {
            "ls_provider": self._langsmith_provider_name(provider),
            "ls_model_name": model,
            "usage_metadata": usage,
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "cost_source": cost_source,
            "estimated_cost_currency": self._cost_currency(),
        }
        if estimated_cost is not None:
            metadata["estimated_cost"] = round(float(estimated_cost), 8)
        return {key: value for key, value in metadata.items() if value not in (None, "", [], {})}

    def _llm_trace_metadata(self, *, feature: str, provider: str, model: str, metadata: dict[str, Any]) -> dict[str, Any]:
        """Return metadata required by LangSmith to identify a costed LLM run."""
        return {
            **metadata,
            "feature": feature,
            "provider": provider,
            "model": model,
            "ls_provider": self._langsmith_provider_name(provider),
            "ls_model_name": model,
            "ls_invocation_params": {"model": model},
        }

    def _llm_trace_output(self, result: Any, cost_metadata: dict[str, Any]) -> dict[str, Any]:
        """Return a LangSmith-friendly LLM output envelope with token usage.

        LangSmith cost tracking expects token counts either as a top-level
        ``usage_metadata`` output field or attached to the current run tree. The
        actual app result is kept in the caller's holder; this output is only
        the trace-friendly representation of the provider call.
        """
        if isinstance(result, str):
            content = self.output_summary(result)
        else:
            content = self.output_summary(result)
        output: dict[str, Any] = {
            "message": {
                "role": "assistant",
                "content": content if isinstance(content, str) else str(content)[:2000],
            },
            "result_summary": content,
        }
        usage = cost_metadata.get("usage_metadata")
        if usage:
            output["usage_metadata"] = usage
        # LangSmith also supports direct cost fields for custom/non-linear
        # pricing. They are estimates from our local config, so include them
        # only as explicit custom fields without pretending they are billing.
        if cost_metadata.get("estimated_cost") is not None:
            output["total_cost"] = cost_metadata.get("estimated_cost")
        return output

    def _attach_usage_to_current_langsmith_run(self, cost_metadata: dict[str, Any]) -> None:
        """Best-effort runtime attachment of usage metadata to current LangSmith run.

        Newer LangSmith docs recommend setting usage_metadata on the current run
        tree from inside the @traceable function. Keep this defensive because
        older SDK versions may expose slightly different attributes.
        """
        usage = cost_metadata.get("usage_metadata")
        if not usage:
            return
        get_current_run_tree = None
        try:
            from langsmith.run_helpers import get_current_run_tree as _get_current_run_tree  # type: ignore

            get_current_run_tree = _get_current_run_tree
        except Exception:
            try:
                from langsmith import get_current_run_tree as _get_current_run_tree  # type: ignore

                get_current_run_tree = _get_current_run_tree
            except Exception:
                get_current_run_tree = None
        if get_current_run_tree is None:
            return
        try:
            run_tree = get_current_run_tree()
        except Exception:
            return
        if run_tree is None:
            return

        # Preferred public shape: usage_metadata on the run itself.
        try:
            setattr(run_tree, "usage_metadata", usage)
        except Exception:
            pass

        # Also mirror it into metadata/extra for SDK versions that serialize
        # metadata only at patch/end time.
        try:
            metadata = dict(getattr(run_tree, "metadata", {}) or {})
            metadata.update(
                {
                    "usage_metadata": usage,
                    "input_tokens": cost_metadata.get("input_tokens"),
                    "output_tokens": cost_metadata.get("output_tokens"),
                    "total_tokens": cost_metadata.get("total_tokens"),
                }
            )
            if cost_metadata.get("estimated_cost") is not None:
                metadata["estimated_cost"] = cost_metadata.get("estimated_cost")
                metadata["estimated_cost_currency"] = cost_metadata.get("estimated_cost_currency")
            run_tree.metadata = {key: value for key, value in metadata.items() if value not in (None, "", [], {})}
        except Exception:
            pass

        try:
            extra = getattr(run_tree, "extra", None)
            if isinstance(extra, dict):
                extra.setdefault("metadata", {})
                if isinstance(extra["metadata"], dict):
                    extra["metadata"].update({"usage_metadata": usage})
                extra["usage_metadata"] = usage
        except Exception:
            pass

    def tts_cost_metadata(
        self,
        *,
        provider: str,
        model: str,
        text: str,
        cache_hit: bool,
    ) -> dict[str, Any]:
        chars = len(str(text or ""))
        provider_key = self._provider_key(provider)
        rate = self._env_float(f"{provider_key}_COST_PER_1000_CHARS")
        if provider_key == "OPENAI":
            rate = rate if rate is not None else self._env_float("OPENAI_TTS_COST_PER_1000_CHARS")
        if provider_key == "GEMINI":
            rate = rate if rate is not None else self._env_float("GEMINI_TTS_COST_PER_1000_CHARS")
        estimated_cost = 0.0 if cache_hit else None
        if estimated_cost is None and rate is not None:
            estimated_cost = chars * float(rate) / 1000
        data: dict[str, Any] = {
            "provider": provider,
            "model": model,
            "ls_provider": self._langsmith_provider_name(provider),
            "ls_model_name": model,
            "characters": chars,
            "cache_hit": cache_hit,
            "cost_source": "cache_hit" if cache_hit else "configured_tts_estimate",
            "cost_currency": self._cost_currency(),
        }
        if estimated_cost is not None:
            data["estimated_cost"] = round(float(estimated_cost), 8)
        return data

    def cost_summary_text(self) -> str:
        if not self._events:
            return "Cost summary: no events yet. Generate a card or audio to populate estimates."
        last_cost = next((event for event in self._events if event.total_tokens or event.estimated_cost is not None), None)
        last = "Last costed run: not available yet."
        if last_cost is not None:
            cost = "rate not configured" if last_cost.estimated_cost is None else f"{last_cost.estimated_cost:.6f} {last_cost.cost_currency}"
            tokens = f"{last_cost.total_tokens} tokens" if last_cost.total_tokens else "no token count"
            last = f"Last costed run: {last_cost.feature} · {last_cost.provider} {last_cost.model} · {tokens} · {cost}"
        session_cost = f"{self.session_estimated_cost:.6f} {self._cost_currency()}" if self.session_costed_runs else "rate not configured"
        return (
            f"{last}\n"
            f"Current session: {self.session_runs} events · {self.session_total_tokens} tokens · estimated cost {session_cost} · "
            f"TTS cache hits {self.session_tts_cache_hits}\n"
            "Costs are estimates. LangSmith can show token/cost metadata when provider/model and usage are available."
        )

    def _metadata_value(self, value: Any) -> Any:
        """Keep operational metadata readable while avoiding huge payloads."""
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            return value.strip()[:500]
        if isinstance(value, (list, tuple, set)):
            return [self._metadata_value(item) for item in list(value)[:20]]
        if isinstance(value, dict):
            return {str(k): self._metadata_value(v) for k, v in value.items()}
        return str(value)[:500]

    def _base_metadata(self, feature: str, provider: str, model: str, metadata: dict[str, Any] | None) -> dict[str, Any]:
        base = self.feature_defaults(feature)
        combined = {
            "app": "AI Anki Language Assistant",
            "feature": feature,
            "provider": provider,
            "model": model,
            **base,
            **(metadata or {}),
            "redaction": "ON" if self.redact_inputs else "OFF",
        }
        return {str(key): self._metadata_value(value) for key, value in combined.items() if value not in (None, "", [], {})}

    def _quality_detail(self, quality: QualitySnapshot, fallback_detail: str = "") -> str:
        parts: list[str] = []
        if quality.outcome:
            parts.append(f"outcome={quality.outcome}")
        if quality.validation_passed is not None:
            parts.append(f"validation_passed={quality.validation_passed}")
        if quality.red_flags_count is not None:
            parts.append(f"red_flags={quality.red_flags_count}")
        if quality.issue_type:
            parts.append(f"issue_type={quality.issue_type}")
        if fallback_detail:
            parts.append(fallback_detail)
        return " | ".join(parts)

    def _run_plain(
        self,
        *,
        feature: str,
        provider: str,
        model: str,
        call_fn: Callable[[], Any],
        metadata: dict[str, Any],
        disabled_detail: str,
        usage_fn: Callable[[], Any] | None = None,
        inputs: dict[str, Any] | None = None,
    ) -> Any:
        start = time.perf_counter()
        try:
            result = call_fn()
        except Exception as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            defaults = self.feature_defaults(feature)
            self._record_event(
                feature=feature,
                provider=provider,
                model=model,
                status="error",
                latency_ms=latency_ms,
                sent_to_langsmith=False,
                detail=str(exc),
                prompt_version=str(metadata.get("prompt_version") or defaults.get("prompt_version") or "unknown"),
                source=str(metadata.get("source") or defaults.get("source") or "unknown"),
                outcome="error",
            )
            raise
        latency_ms = int((time.perf_counter() - start) * 1000)
        quality = self.quality_snapshot(feature, result)
        usage_metadata = usage_fn() if usage_fn else None
        cost_metadata = self._cost_metadata_for_call(
            provider=provider,
            model=model,
            inputs=inputs or {},
            result=result,
            usage_metadata=usage_metadata,
        )
        defaults = self.feature_defaults(feature)
        self._record_event(
            feature=feature,
            provider=provider,
            model=model,
            status="ok" if not self.enabled else "not_sent",
            latency_ms=latency_ms,
            sent_to_langsmith=False,
            detail=self._quality_detail(quality, disabled_detail),
            prompt_version=str(metadata.get("prompt_version") or defaults.get("prompt_version") or "unknown"),
            source=str(metadata.get("source") or defaults.get("source") or "unknown"),
            validation_passed=quality.validation_passed,
            red_flags_count=quality.red_flags_count,
            issue_type=quality.issue_type,
            outcome=quality.outcome,
            input_tokens=cost_metadata.get("input_tokens"),
            output_tokens=cost_metadata.get("output_tokens"),
            total_tokens=cost_metadata.get("total_tokens"),
            estimated_cost=cost_metadata.get("estimated_cost"),
            cost_currency=str(cost_metadata.get("estimated_cost_currency") or self._cost_currency()),
            cost_source=str(cost_metadata.get("cost_source") or ""),
        )
        return result

    def trace_call(
        self,
        *,
        feature: str,
        provider: str,
        model: str,
        inputs: dict[str, Any],
        metadata: dict[str, Any] | None,
        call_fn: Callable[[], Any],
        usage_fn: Callable[[], Any] | None = None,
    ) -> Any:
        """Run call_fn, optionally sending a LangSmith trace and always logging locally."""
        traceable = self._load_traceable() if self.enabled else None
        can_send = bool(self.enabled and traceable and self.api_key_configured)
        safe_inputs = self.sanitize_value(inputs)
        safe_metadata = self._base_metadata(feature, provider, model, metadata)

        if not can_send:
            detail = self.last_error if self.enabled else "LangSmith disabled; local event only."
            return self._run_plain(
                feature=feature,
                provider=provider,
                model=model,
                call_fn=call_fn,
                metadata=safe_metadata,
                disabled_detail=detail,
                usage_fn=usage_fn,
                inputs=inputs,
            )

        holder: dict[str, Any] = {}
        start = time.perf_counter()

        def _run_traced(payload: dict[str, Any]) -> dict[str, Any]:
            llm_metadata = self._llm_trace_metadata(
                feature=feature,
                provider=provider,
                model=model,
                metadata=safe_metadata,
            )

            def _run_provider_call(_: dict[str, Any]) -> dict[str, Any]:
                try:
                    result = call_fn()
                except Exception as exc:
                    holder["provider_exception"] = exc
                    raise
                quality = self.quality_snapshot(feature, result)
                usage_metadata = usage_fn() if usage_fn else None
                cost_metadata = self._cost_metadata_for_call(
                    provider=provider,
                    model=model,
                    inputs=inputs,
                    result=result,
                    usage_metadata=usage_metadata,
                )
                holder["result"] = result
                holder["quality"] = quality
                holder["cost_metadata"] = cost_metadata
                self._attach_usage_to_current_langsmith_run(cost_metadata)
                return self._llm_trace_output(result, cost_metadata)

            # Cost tracking in LangSmith is most reliable when the actual model
            # call is its own child run with run_type="llm", ls_provider,
            # ls_model_name and top-level usage_metadata. The outer run remains
            # the app workflow (vocabulary_card_generation, batch, grammar, etc.).
            try:

                @traceable(  # type: ignore[misc]
                    name=f"{feature}.llm",
                    run_type="llm",
                    metadata=llm_metadata,
                    tags=[
                        "ai-anki",
                        "llm-call",
                        str(provider),
                        str(feature),
                        str(safe_metadata.get("prompt_version", "unknown")),
                    ],
                )
                def _langsmith_llm_call(llm_payload: dict[str, Any]) -> dict[str, Any]:
                    return _run_provider_call(llm_payload)

            except TypeError:

                @traceable(name=f"{feature}.llm")  # type: ignore[misc]
                def _langsmith_llm_call(llm_payload: dict[str, Any]) -> dict[str, Any]:
                    return _run_provider_call(llm_payload)

            llm_trace_output = _langsmith_llm_call(payload)
            result = holder.get("result")
            quality = holder.get("quality") or self.quality_snapshot(feature, result)
            cost_metadata = holder.get("cost_metadata") or {}
            runtime_metadata = {**safe_metadata, **cost_metadata}
            return {
                "workflow": feature,
                "inputs": payload,
                "llm_run": {
                    "provider": provider,
                    "model": model,
                    "usage_metadata": cost_metadata.get("usage_metadata"),
                    "estimated_cost": cost_metadata.get("estimated_cost"),
                },
                "llm_output": llm_trace_output,
                "result_summary": self.output_summary(result),
                "quality_metrics": quality.as_metadata(),
                "cost_metadata": cost_metadata,
                "metadata": runtime_metadata,
            }

        try:
            # Outer workflow trace stays a chain; the real provider request is
            # logged as an LLM child run inside _run_traced so LangSmith can show
            # token/cost details without losing app-level workflow metadata.
            try:

                @traceable(  # type: ignore[misc]
                    name=feature,
                    run_type="chain",
                    metadata=safe_metadata,
                    tags=[
                        "ai-anki",
                        "workflow",
                        str(provider),
                        str(feature),
                        str(safe_metadata.get("prompt_version", "unknown")),
                        str(safe_metadata.get("source", "unknown")),
                    ],
                )
                def _langsmith_traced_call(payload: dict[str, Any]) -> dict[str, Any]:
                    return _run_traced(payload)

            except TypeError:

                @traceable(name=feature)  # type: ignore[misc]
                def _langsmith_traced_call(payload: dict[str, Any]) -> dict[str, Any]:
                    return _run_traced(payload)

            _langsmith_traced_call(safe_inputs)
            self._wait_for_tracers()
            result = holder.get("result")
            quality = holder.get("quality") or self.quality_snapshot(feature, result)
            cost_metadata = holder.get("cost_metadata") or {}
            latency_ms = int((time.perf_counter() - start) * 1000)
            self._record_event(
                feature=feature,
                provider=provider,
                model=model,
                status="ok",
                latency_ms=latency_ms,
                sent_to_langsmith=True,
                detail=self._quality_detail(quality, f"Sent to LangSmith project: {self.project_name}"),
                prompt_version=str(safe_metadata.get("prompt_version") or "unknown"),
                source=str(safe_metadata.get("source") or "unknown"),
                validation_passed=quality.validation_passed,
                red_flags_count=quality.red_flags_count,
                issue_type=quality.issue_type,
                outcome=quality.outcome,
                input_tokens=cost_metadata.get("input_tokens"),
                output_tokens=cost_metadata.get("output_tokens"),
                total_tokens=cost_metadata.get("total_tokens"),
                estimated_cost=cost_metadata.get("estimated_cost"),
                cost_currency=str(cost_metadata.get("estimated_cost_currency") or self._cost_currency()),
                cost_source=str(cost_metadata.get("cost_source") or ""),
            )
            return result
        except Exception as exc:
            if "provider_exception" in holder:
                latency_ms = int((time.perf_counter() - start) * 1000)
                self._record_event(
                    feature=feature,
                    provider=provider,
                    model=model,
                    status="error",
                    latency_ms=latency_ms,
                    sent_to_langsmith=False,
                    detail=str(holder["provider_exception"]),
                    prompt_version=str(safe_metadata.get("prompt_version") or "unknown"),
                    source=str(safe_metadata.get("source") or "unknown"),
                    outcome="error",
                )
                raise holder["provider_exception"]
            if "result" in holder:
                # The provider call succeeded but LangSmith reporting failed. Do
                # not break the app; keep the generated card and record locally.
                result = holder["result"]
                quality = holder.get("quality") or self.quality_snapshot(feature, result)
                cost_metadata = holder.get("cost_metadata") or {}
                latency_ms = int((time.perf_counter() - start) * 1000)
                self._record_event(
                    feature=feature,
                    provider=provider,
                    model=model,
                    status="ok_not_sent",
                    latency_ms=latency_ms,
                    sent_to_langsmith=False,
                    detail=self._quality_detail(quality, f"LangSmith send failed after generation: {exc}"),
                    prompt_version=str(safe_metadata.get("prompt_version") or "unknown"),
                    source=str(safe_metadata.get("source") or "unknown"),
                    validation_passed=quality.validation_passed,
                    red_flags_count=quality.red_flags_count,
                    issue_type=quality.issue_type,
                    outcome=quality.outcome,
                    input_tokens=cost_metadata.get("input_tokens"),
                    output_tokens=cost_metadata.get("output_tokens"),
                    total_tokens=cost_metadata.get("total_tokens"),
                    estimated_cost=cost_metadata.get("estimated_cost"),
                    cost_currency=str(cost_metadata.get("estimated_cost_currency") or self._cost_currency()),
                    cost_source=str(cost_metadata.get("cost_source") or ""),
                )
                return result

            return self._run_plain(
                feature=feature,
                provider=provider,
                model=model,
                call_fn=call_fn,
                metadata=safe_metadata,
                disabled_detail=f"LangSmith wrapper failed before provider call: {exc}",
                usage_fn=usage_fn,
                inputs=inputs,
            )


TRACER = LlmOpsTracer()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


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

    def _model_for_workflow(self, workflow: str = "card") -> str:
        resolver = getattr(self._inner, "model_for_workflow", None)
        if callable(resolver):
            try:
                return str(resolver(workflow))
            except Exception:
                return self._model
        return self._model

    def _trace(
        self,
        feature: str,
        inputs: dict[str, Any],
        call_fn: Callable[[], Any],
        *,
        metadata: dict[str, Any] | None = None,
        workflow: str = "card",
    ) -> Any:
        model = self._model_for_workflow(workflow)
        defaults = TRACER.feature_defaults(feature)
        base_metadata = {
            "feature": feature,
            "provider": self.provider_name,
            "model": model,
            "workflow_model_role": workflow or "card",
            "app": "AI Anki Language Assistant",
            **defaults,
            **(metadata or {}),
        }
        return TRACER.trace_call(
            feature=feature,
            provider=self.provider_name,
            model=model,
            inputs=inputs,
            metadata=base_metadata,
            call_fn=call_fn,
            usage_fn=lambda: getattr(self._inner, "_last_usage_metadata", None),
        )

    def _generate_text(self, prompt: str, workflow: str = "card") -> str:
        generate_text = getattr(self._inner, "_generate_text")

        def _call_generate_text() -> str:
            try:
                return generate_text(prompt, workflow=workflow)
            except TypeError:
                return generate_text(prompt)

        return self._trace(
            "raw_text_generation",
            {"prompt": prompt, "purpose": "direct prompt call", "workflow": workflow},
            _call_generate_text,
            metadata={"source": f"direct_{workflow}_prompt_call", "workflow_model_role": workflow},
            workflow=workflow,
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
            metadata={"source": "single_flashcard"},
            workflow="card",
        )

    def start_conversation(self, topic: str, target_language: str) -> ConversationStart:
        return self._trace(
            "conversation_start",
            {"topic": topic, "target_language": target_language},
            lambda: self._inner.start_conversation(topic, target_language),
            workflow="card",
        )

    def analyze_grammar(self, sentence: str, target_language: str) -> GrammarAnalysis:
        return self._trace(
            "grammar_analysis",
            {"sentence": sentence, "target_language": target_language},
            lambda: self._inner.analyze_grammar(sentence, target_language),
            workflow="card",
        )

    def generate_grammar_card(
        self, grammar_item: str, target_language: str, topic_context: str = ""
    ) -> GrammarAnalysis:
        source = "batch_grammar"
        if any(token in str(topic_context or "").casefold() for token in ("source", "ocr", "import", "rule-only", "detected")):
            source = "import_material_grammar"
        return self._trace(
            "grammar_card_generation",
            {"grammar_item": grammar_item, "target_language": target_language, "topic_context": topic_context},
            lambda: self._inner.generate_grammar_card(grammar_item, target_language, topic_context),
            metadata={"source": source},
            workflow="import" if source == "import_material_grammar" else "card",
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
            workflow="card",
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
            metadata={"improvement_level": improvement_level, "feedback_language": feedback_language},
            workflow="review",
        )


def wrap_ai_client(client: VocabularyAiClient) -> VocabularyAiClient:
    if isinstance(client, TracedVocabularyAiClient):
        return client
    return TracedVocabularyAiClient(client)
