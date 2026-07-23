# v8.1.5.10 — Override + Add this card + placeholder validation hotfix

This hotfix fixes two workflow regressions in Batch review:

- `Add this card` now respects `quality_override=True` after the user clicks `Approve warning` / `Ignore warning`.
- If a card still has HARD warnings and no override, `Add this card` now asks whether to approve and add anyway instead of forcing edit/regenerate.
- `Add all ready` also explicitly skips re-blocking cards that have `quality_override=True`.
- The local example validator now accepts regular inflected forms in placeholder phrases, e.g. `yell at someone` → `yelled at the players`.

The intended flow is now:

1. Validator warns.
2. User clicks `Approve warning` or confirms from `Add this card`.
3. Card is marked ready with `quality_override=True`.
4. Both `Add this card` and `Add all ready` can add it.
