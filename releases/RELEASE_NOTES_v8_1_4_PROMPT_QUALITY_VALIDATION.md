# v8.1.4 — Prompt quality and validation

This release focuses on generated-card quality rather than UI expansion.

## Changes

- Upgraded the vocabulary prompt to `v5-topic-quality-validation`.
- Added stronger exact-input, phrase-level, explanation-language, and topic/context rules.
- Added user-defined topic handling: the topic remains free text typed by the user. Presets are only optional hints when a known domain is detected.
- Added provider self-check fields:
  - `topic_fit`
  - `topic_warning`
  - `quality_warnings`
- Added local quality validation in `src/quality/card_validator.py`.
- Added language-aware validation for explanation languages:
  - Polish
  - Spanish
  - English
  - German
  - Italian
  - No translation
- Added hard warnings for obvious serious issues:
  - input phrase changed
  - target language mismatch
  - explanation language mismatch
  - Cyrillic in non-Cyrillic explanation fields
  - Polish examples such as `nostalgja`, `głęboka smutek`, `область живота`
  - required fields missing
- Added soft warnings for likely topic mismatch, mixed-language text, and provider self-check warnings.
- Batch preview now preserves topic fit and quality warning metadata in autosave.
- Claude provider now accepts `topic_context`, matching Gemini/OpenAI.

## What this does not do

- It is not a full grammar checker.
- It does not use LangGraph.
- It does not force topics into a closed list.
- It does not block every imperfect card automatically; warnings require user confirmation before adding to Anki.

## Tests

- `python -m compileall src tests`
- `pytest -q tests/ai/test_prompt_quality_validation.py tests/ai/test_prompts_topics.py tests/anki tests/speech`
