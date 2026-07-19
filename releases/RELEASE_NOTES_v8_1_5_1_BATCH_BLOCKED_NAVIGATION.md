# v8.1.5.1 — Batch blocked-card navigation hotfix

## Fixed

- `Add all ready` no longer blocks the whole operation when only some ready cards have HARD quality warnings.
- Valid ready cards are still added to Anki.
- Cards with HARD warnings are marked as `blocked_quality_warning` and skipped until edited or regenerated.
- Added Batch navigation buttons:
  - `Go to first blocked`
  - `Next blocked / failed`
  - `Show issue summary`
- Removed the over-aggressive Polish-field warning for Spanish-specific characters. Polish explanation fields may quote target-language Spanish words; Cyrillic remains a HARD warning.
- Soft warnings no longer interrupt `Add all ready`.

## Why

Earlier builds could stop the entire Add All workflow because a small number of cards had HARD quality warnings, even though many other cards were valid. The user also had no practical way to jump to the blocked cards from the Batch UI.

## Tests

- `python -m compileall src tests`
- `pytest -q tests/ai/test_prompt_quality_validation.py tests/ai/test_prompts_topics.py tests/anki tests/speech`
