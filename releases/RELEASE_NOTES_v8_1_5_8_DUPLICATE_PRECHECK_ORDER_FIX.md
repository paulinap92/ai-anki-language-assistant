# v8.1.5.8 — Duplicate Precheck Order Fix

Hotfix for Batch duplicate handling.

## Fixed

- Auto Batch duplicate precheck now runs before provider generation and updates the UI with an explicit `Duplicate precheck before AI` message.
- Pending items are checked using conservative duplicate lookup candidates, not only the raw pasted line. This catches common input formats such as:
  - `word<TAB>translation`
  - `word    translation`
  - `word - part of speech`
  - `target | provided sentence`
- `Generate selected` also performs a last-resort duplicate precheck before any provider API call when the item is still pending and not generated.
- Duplicate precheck now covers all pending Batch modes instead of only Vocabulary/Provided examples. Grammar items can also be skipped before provider calls when the same sentence/structure already exists.
- When a duplicate is detected before generation, the row is marked `duplicate_found` or `duplicate_uncertain` and no AI provider API is used.

## Why

Some Batch messages made it look like cards were generated first and duplicates were only checked during `Add all ready`. In table/OCR-style pasted lists, duplicate precheck could miss existing cards because it compared the full raw line instead of the actual target item. This fix restores the intended order: Anki duplicate scan first, provider API second.

## Tests

- `python -m compileall -q src tests`
- `pytest -q tests/ai/test_batch_grammar_prompt.py tests/ai/test_prompt_quality_validation.py tests/ai/test_prompts_topics.py tests/anki tests/speech`
