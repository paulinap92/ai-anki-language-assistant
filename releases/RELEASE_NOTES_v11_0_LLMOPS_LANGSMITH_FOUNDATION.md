# v11.0 — LLMOps / LangSmith Foundation

## Added

- Optional LangSmith tracing foundation through a lightweight wrapper around AI providers.
- New `LLMOps / LangSmith` tab in the modern GUI.
- Local AI event log visible even when LangSmith is disabled.
- `Test trace`, `Refresh status`, `Clear local log`, `Copy .env setup`, and `Open LangSmith` actions.
- Environment settings:
  - `LANGSMITH_TRACING`
  - `LANGSMITH_API_KEY`
  - `LANGSMITH_PROJECT`
  - `LANGSMITH_REDACT_INPUTS`
- Redaction-first design: source text/prompts/outputs are summarized by default.
- Documentation in `docs/LLMOPS_LANGSMITH.md`.

## Traced flows

- Single vocabulary card generation.
- Batch vocabulary generation.
- Batch grammar generation.
- Provided-example generation.
- Conversation Practice start and feedback.
- Raw AI calls used by Import Material AI candidate extraction.

## Notes

- The app still works normally when LangSmith is not installed or disabled.
- `LANGSMITH_REDACT_INPUTS=true` is recommended for screenshots/book OCR material.
- Streamlit dashboard over LangSmith runs is planned for the next milestone.

## Tests

- `python -m py_compile src/ui/modern_gui.py src/core/config.py src/ai/factory.py src/observability/langsmith_tracing.py`
- `python -m compileall -q src`
- `python -m pytest -q tests/observability/test_langsmith_tracing.py tests/ai/test_batch_grammar_prompt.py`
