# v8.1.5.7 — Audio Tab Scope Cleanup

Small UI hotfix after pre-OCR cleanup.

## Changed

- Hide the global Card AI provider / Target language / Anki deck bar while the user is in `Speech / Audio`.
- Added an explicit `Anki deck to scan` selector inside `Speech / Audio`, bound to the same deck variable used elsewhere.
- Added `Refresh decks` inside `Speech / Audio` so audio scanning does not depend on the hidden global top bar.
- Clarified Audio provider copy: it is used only for TTS/audio generation; Card AI settings are hidden in this tab.

## Why

The Audio tab should not visually expose card-generation controls. It should focus on audio provider, voice/model, deck scanning, filters and audio status.

## Tests

- `python -m compileall -q src tests`
- `pytest -q tests/ai/test_batch_grammar_prompt.py tests/ai/test_prompt_quality_validation.py tests/ai/test_prompts_topics.py tests/anki tests/speech`
