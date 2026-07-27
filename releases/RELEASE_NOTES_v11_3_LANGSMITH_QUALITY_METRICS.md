# v11.3 — LangSmith Quality Metrics

This release turns the existing LangSmith/LLMOps foundation into a more useful quality-observability layer.

## Added

- Quality metadata for generated AI cards:
  - `validation_passed`
  - `red_flags_count`
  - `issue_type`
  - `outcome`
- Feature/source metadata for traced calls:
  - `single_flashcard`
  - `batch_queue`
  - `batch_grammar`
  - `grammar_tab`
  - `conversation_practice`
  - `import_material_grammar`
- Prompt-version metadata for major workflows.
- Local LLMOps outcome events for reviewed cards:
  - `added_to_anki`
  - `updated_existing_note`
  - `skipped`
  - `duplicate_skipped`
  - `duplicate_uncertain`
  - `add_failed`
- More readable local event log in the `LLMOps / LangSmith` tab.
- Safer tracing fallback: LangSmith errors do not break card generation.

## Improved

- LangSmith status wording now says `configured but inactive: package missing` instead of the misleading `enabled, but package is missing`.
- The button is now labelled `Open LangSmith app` and opens `https://smith.langchain.com/`.
- Metadata stays readable even when input/output redaction is ON.
- Redaction still summarizes pasted text/prompts/outputs before external tracing.

## Notes

LangSmith remains optional. The app still runs with tracing disabled, without an API key, or without the `langsmith` package installed.
