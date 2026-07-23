# v8.1.5.15 — Stale quality warning sync fix

Small Batch/Provided Examples hotfix.

## Fixed

- Batch preview no longer displays stale `quality_warnings` from older autosaves or earlier validator versions.
- Provided examples cards such as `microorganisms | Bacteria are microorganisms which often cause disease.` are revalidated on display using only the target item, not the full `target | sentence` row.
- If a card was previously marked `blocked_quality_warning` but current validation no longer finds a HARD warning, the item is moved back to `ready` and the stale blocking error is cleared.
- `Approve warning` now handles stale warnings cleanly:
  - if the old preview had a HARD warning but current validation is clean, it clears the stale warning and marks the card ready;
  - it no longer shows the confusing “No hard warnings” popup while the preview still displays an old HARD warning.
- `Add this card` uses the same fresh validation sync before deciding whether warnings should block or ask for manual approval.

## Not changed

- No OCR/STT changes.
- No new provider behavior.
- No changes to the core card schema.
