# v10.5 Import UX + Suggestions Queue Fix

## Focus

This release cleans up the two confusing UX areas from v10.4:

1. Import Material candidate flow.
2. Conversation Practice suggested expressions flow.

## Import Material UX

- Renamed the source text panel to **Reviewed source text**.
- Renamed candidate-finding sections to:
  - **Find from text without AI**
  - **Find from text with AI**
  - **Candidate drafts / cherry-pick**
- Removed the full **Manual candidate builder** from the main Import Material sidebar.
- Added a small **+ Add missing candidate** button in the candidate drafts area.
- The missing-candidate dialog can fill target/example from the current Reviewed source text selection.
- The main action is now **Add selected to Batch / Queue**.

## Suggested expressions

- Reworked Conversation Practice suggestions into a draft flow:
  - AI suggestions
  - checkbox
  - inline edit
  - remove
  - Add selected to queue
  - Selected for Anki
- Queue creation now reads the current edited UI values, not the original AI response strings.
- Renamed **Flashcard queue** to **Selected for Anki**.
- Added clearer empty state for suggestions.

## Notes

- The existing OCR quality gate remains in place: **Good / Medium / Poor** with a warning before candidate extraction on poor OCR.
- The v10.4 grammar candidate safeguards are preserved: Grammar targets are not destroyed when using grammar actions.
