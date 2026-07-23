# v8.1.5.4 — Batch mode persistence hotfix

## Fixed

- Fixed a Batch UI bug where selecting `Grammar` mode could be silently reset back to `Vocabulary` when the current pending item was refreshed or selected.
- The Batch mode dropdown is now treated as a session-level choice for pending/not-yet-generated items.
- Changing Batch mode now applies the selected mode to all pending/not-generated rows and autosaves the session.
- Generated, added, duplicate, blocked, invalid, and skipped rows keep their stored mode so reviewed cards are not rewritten accidentally.

## Why

A list could be loaded while the default mode was `Vocabulary`; then the user selected `Grammar` and clicked generate, but the UI could restore the pending item's old stored `batch_mode`, making it look like the app ignored the user's choice.

## Validation

- `python -m compileall src tests`
- `pytest -q tests/ai/test_batch_grammar_prompt.py tests/ai/test_prompt_quality_validation.py tests/ai/test_prompts_topics.py tests/anki tests/speech`
