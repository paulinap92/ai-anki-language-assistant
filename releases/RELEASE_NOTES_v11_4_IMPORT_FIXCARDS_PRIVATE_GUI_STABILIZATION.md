# v11.4 — Import/Fix Cards/Private GUI stabilization

This hotfix stabilizes the workflows found during final manual testing.

## Fixed

- Private GUI no longer removes the useful top controls. It hides the public app header/title only, while keeping `Card AI provider`, `Target language`, and `Anki deck` visible.
- Added a discreet private launcher:
  - `main_gui_custom_private.py`
  - `run_gui_custom_private.bat`
- Restored neutral app icon assets in `assets/`.
- Import Material / Smart Grammar candidates no longer silently fall back to `Provided example` when Smart Grammar is selected.
- Candidate extraction now has its own `Candidate AI provider` selector, so OCR/import candidate extraction can use a different configured provider from card generation.
- AI candidate extraction is disabled while a request is already running, preventing repeated-click floods.
- AI candidate extraction replaces the current AI candidate set instead of appending silently.
- JSON/schema fragments such as `{`, `"type": "grammar"`, `source_type`, and `strategy` are filtered out and cannot become candidate cards.
- Candidate rendering is capped for excessive AI output so the GUI does not freeze on hundreds of drafts.
- `Clean extracted text` now gives visible feedback and removes common OCR/image markdown artifacts.
- Fix Cards now supports `Search scope`:
  - `Selected deck only`
  - `All decks`
- Fix Cards now has a visible `Regenerate selected card` workflow that opens the editor, generates a preview, and saves back to the same Anki note.
- Grammar add-to-Anki now uses an exact `Sentence` precheck and allows repeated grammar structures with different sentences, reducing false duplicate blocks.

## Not changed

- No full table-aware OCR parser yet.
- No new Anki note type.
- No automatic old-card migration.
- No LangGraph/cloud agent/web rewrite.

## Validation

- `python -m py_compile src/ui/modern_gui.py src/ai/prompts.py src/anki/client.py main_gui_custom.py main_gui_custom_private.py`
- `python -m compileall -q src main_gui_custom.py main_gui_custom_private.py`
