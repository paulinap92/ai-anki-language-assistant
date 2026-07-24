# v10.3 Candidate Flow Trial

Small UX trial focused on Import Material / Cherry Pick / Batch editing.

## Import Material

- Reworded the flow to make the intended pipeline explicit:
  1. import / OCR,
  2. review and clean source text,
  3. create candidate drafts,
  4. edit drafts,
  5. cherry-pick final candidates,
  6. send edited candidates to Batch / Queue.
- Renamed the candidate area conceptually to **Candidate drafts / cherry-pick**.
- Added an **Edit** button for each candidate draft.
- Candidate edits now persist in the candidate object and refresh the candidate list.
- Candidate cards show `source` and `edited` badges.
- Sending candidates to Batch carries source/edited metadata forward.

## Batch / Queue

- Added **Save item edit** next to the Current item entry.
- Saving a Batch item edit updates the underlying Batch item state, refreshes preview/progress, and autosaves the session.
- If the edited text differs from the previous item, stale generated card/grammar payloads are cleared so generation cannot use old content.

## Scope

This is a trial version. It does not redesign the full Import Material layout yet; it adds persistence and clearer flow labels so the current UI can be tested safely.
