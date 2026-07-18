# v8.1.3 Hotfix — Batch/API safety, Audio progress, Fix Cards visibility

This hotfix focuses on workflow correctness and user-visible feedback.

## Batch / Auto Batch

- Auto Batch now runs a broad Anki duplicate precheck before provider API calls.
- Pending items that already exist in Anki are marked as `duplicate_found` or `duplicate_uncertain` and are not sent to Gemini/OpenAI/Claude.
- If AnkiConnect is unavailable, Auto Batch is cancelled before provider API calls to avoid wasting quota.
- `Add all ready` now stores user-facing failure reasons per card.
- Final Add All summary now includes short failed-details examples instead of only a failed count.
- Duplicate errors reported by Anki during add are treated as duplicate/uncertain, not generic failed.

## Speech / Audio

- Audio batch now refreshes the visible list/progress after each item, not only at the end.
- User-facing progress messages are also recorded in activity/log status.

## Fix Cards

- `Fix selected card` now reports when zero/multiple cards are selected.
- The selected card preview is refreshed before opening the editor.
- The editor is raised/focused and uses a modal grab so it should not silently open behind the main window.

## UI wording

- Removed Polish `dział` wording from the app UI and documentation; use `topic/context` consistently.
