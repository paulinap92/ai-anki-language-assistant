# v8.1.1 — Audio / Fix Cards cleanup

This release cleans up the v8.1 UI logic after the first Existing Cards implementation.

## Changed

- Moved missing-audio discovery back to **Speech / Audio** as the central audio workflow.
- Updated **Speech / Audio** to scan existing notes broadly through the generic Anki note scanner instead of only the app's custom `AI Vocabulary Light Card` note type.
- Added an optional extra Anki query field to **Speech / Audio** for filters such as `tag:topic_character`, `note:Basic`, or `is:due`.
- Renamed **Existing Cards** to **Fix Cards** and moved it after **Speech / Audio** in the tab order.
- Removed the visible missing-audio generation workflow from **Fix Cards** to avoid duplicated logic.
- Reworked **Fix Cards** into a quality-maintenance tab for flagged, leech, tagged, and manually selected cards.
- Added visible filters in **Fix Cards** for:
  - extra Anki query,
  - tag,
  - flag,
  - `tag:leech`,
  - pasted word lists.
- Kept topic tagging and manual card editing in **Fix Cards**.
- Notes without a supported audio field are shown in **Speech / Audio** as `missing_audio_field`, but are not selected for automatic generation by default.

## Not changed

- No OCR.
- No STT.
- No LangGraph.
- No audio cache recovery.
- No note-type migration or automatic field creation for old Anki notes.

## Validation

- `python -m compileall src tests` passes.
- `pytest -q tests/anki tests/ai/test_prompts_topics.py tests/speech` passes.
- Full `pytest -q` still requires optional provider dependencies (`anthropic`, `google.genai`) in this environment.
