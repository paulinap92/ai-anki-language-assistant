# v8.1.5.16 - Warning single source of truth

This hotfix fixes a Batch UI consistency bug where the preview could show a HARD quality warning while the `Approve warning` popup said there were no hard warnings.

## Root cause

Batch vocabulary cards had two warning sources:

1. `card.quality_warnings` stored inside the generated card payload.
2. `item["quality_warnings"]` recomputed by the current local validator.

After Provided examples/parser fixes, old card payload warnings could still render in the preview while the approval/add logic used the recomputed item warnings. This created contradictory UI states.

## Fix

- Revalidate before rendering Batch vocabulary card previews.
- Treat `_sync_quality_warnings_for_item(...)` as the single active warning source.
- Sync active warnings back into:
  - the in-memory `VocabularyCard`,
  - the serialized Batch item card payload,
  - `item["quality_warnings"]`.
- `Approve warning`, `Add this card`, `Add all ready`, and preview now read the same warning list.
- If a HARD warning is visible, `Approve warning` should ask to approve it.
- If there are no active HARD warnings, the preview should not show an active HARD warning.

## Tests

- `python -m compileall -q src tests`
- `pytest -q tests/ai/test_prompt_quality_validation.py tests/ai/test_batch_grammar_prompt.py tests/ai/test_prompts_topics.py tests/anki tests/speech`

Result: 43 passed.
