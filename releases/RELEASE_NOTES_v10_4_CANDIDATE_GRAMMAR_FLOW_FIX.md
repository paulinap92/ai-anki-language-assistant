# v10.4 — Candidate Grammar Flow Fix

Trial fix after Import Material testing.

## Fixed

- AI Assist in Grammar mode now displays candidates with target + example as **Grammar target**, not **provided example**.
- Sentence-only grammar candidates are displayed as **Grammar from sentence**.
- Marking a candidate with **Use for Grammar** preserves an existing target instead of clearing it.
- Sending grammar candidates to Batch preserves `target | example` when both exist; sentence-only candidates still go as sentence-only for Batch inference.
- Renamed misleading **Free local cherry-pick** area to **Find candidates without AI**.
- Updated OCR candidate extraction prompt so Grammar mode asks for a clear grammar target whenever possible.

## Test

Import Material → AI Assist mode: Grammar → find candidates.
Expected cards:

- `Grammar target` when target exists.
- `Grammar from sentence` only when target is empty.
- `Use for Grammar` must not delete target.
