# v8.1.4.1 — Duplicate precheck sanity hotfix

## Fixed

- Auto Batch duplicate precheck now scans the whole Anki collection, not only the selected deck.
- Add all ready duplicate precheck also scans the whole collection before adding.
- This prevents Gemini/OpenAI/Claude/Claude API calls for words that already exist in another deck.
- User-facing duplicate messages now say "Anki collection" to make the scope clear.

## Why

Anki duplicate rejection can happen even when the duplicate is outside the currently selected deck. The previous precheck was deck-scoped, so Auto Batch could still generate cards through the provider API and only fail later at Add all ready.

## Additional safeguard

- Auto Batch now runs the duplicate precheck even when resuming a paused/autosaved session.
- Pending items receive duplicate-precheck metadata so it is clear that the collection-wide check happened before provider generation.
