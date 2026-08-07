# v12.0.4 — Conversation UX, card rotation and coverage

This release fixes the main usability problems found while testing flashcard-based Conversation Practice with a real Anki deck.

## Right-panel UX

- The entire right Conversation panel is now vertically scrollable.
- `Expressions to use next` and `New flashcard candidates` stay near the top.
- `Staged for Batch / Queue` remains directly below the candidates.
- `Flashcards in this session` moved to the bottom and is collapsed by default.
- The collapsed session button shows live coverage, for example `8/30 practised`.
- Expanding the session list shows `✓` for practised targets and `○` for targets not used yet.

## New flashcard candidates

- Flashcard mode can add 0–3 genuinely new candidates per exchange.
- Candidates accumulate across turns instead of being replaced after every answer.
- Existing deck targets, near-duplicates and already staged expressions are still rejected.
- Useful longer collocations around known targets remain allowed.
- Staging a candidate moves it out of the candidate pool and into the staged queue.
- When no new candidate exists, staging controls are disabled and the UI explains why the list is empty.

## Card selection and rotation

Flashcard mode now supports:

- `Continue rotation` — default; consumes a shuffled per-source queue and avoids repeats until the current cycle is exhausted.
- `Anki due cards` — Anki-deck source only; reads cards currently due through AnkiConnect without modifying scheduling state.
- `Random cards` — random session without consuming normal rotation progress.
- `Repeat last session` — deliberately reloads the previous session for the same source.

Rotation progress is saved locally in `conversation_rotation_state.json`. The file is ignored by Git and excluded from clean release packages. Reset clears the current conversation but does not reset rotation progress.

## Tutor coverage

- The app tracks which session targets actually appeared in the conversation.
- Prompt context is rebuilt after each turn with `NOT USED YET` targets before `ALREADY USED` targets.
- The tutor is explicitly told to prefer unused targets and avoid basing two consecutive questions on the same target unless the learner asks for clarification.

## Validation

- Python compile check passed.
- 29 targeted Conversation / Anki / prompt tests passed in the release workspace.
- Live AnkiConnect and visual Windows GUI behaviour still need real-machine testing.
