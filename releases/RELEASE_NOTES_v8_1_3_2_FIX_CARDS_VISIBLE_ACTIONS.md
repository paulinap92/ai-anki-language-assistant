# v8.1.3.2 - Fix Cards visible actions hotfix

## Purpose

Fix Cards looked like a preview-only tab because the main action buttons could be pushed below the left-side panel. This hotfix keeps the core actions visible next to the queue and explains what the tab can actually do.

## Changes

- Added a visible action row on the right side of `Fix Cards`:
  - `Edit selected card`
  - `Apply topic tag`
  - `Select all`
  - `Clear`
- Updated the initial preview instructions to explain the workflow.
- Updated selected-card preview to list the available actions:
  - edit selected card and save to the same Anki note,
  - apply topic tag to selected cards,
  - audio fixes remain in `Speech / Audio`.

## Validation

- `python -m compileall src tests`
- `pytest -q tests/anki tests/ai/test_prompts_topics.py tests/speech`
