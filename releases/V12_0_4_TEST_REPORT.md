# v12.0.4 test report

## Automated checks

- `python -m compileall -q src tests` — passed.
- Targeted pytest suite — 29 passed:
  - conversation suggestion separation;
  - conversation feedback model compatibility;
  - session selection / rotation;
  - Anki deck conversation reader;
  - Anki due-card note lookup;
  - flashcard conversation prompts;
  - flashcard context building.

## Full-suite limitation

- Full `pytest -q` collection was attempted but stopped because optional provider SDKs are not installed in this container: `anthropic` and `google.genai`.

## Not run in this container

- Visual CustomTkinter interaction on Windows.
- Live AnkiConnect deck / due-card query against a real Anki profile.
- Real provider conversation call with OpenAI / Gemini / Claude.
- Ruff was not available in the container.

## Manual checks recommended

1. Start `Talk based on flashcards` with `Continue rotation`; restart a second session and verify a different card set loads.
2. Expand `Flashcards in this session` and verify the practised counter changes as targets appear.
3. Try `Repeat last session` and confirm the exact previous set returns.
4. Try `Anki due cards` with cards due and with no cards due.
5. Scroll the full right panel to the bottom on the normal application window size.
6. Generate several turns with new collocations and verify candidates accumulate, then move to Staged when selected.
