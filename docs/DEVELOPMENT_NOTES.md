# Development Notes

## Current implementation

The application currently includes:

- classic and modern GUIs;
- word-first vocabulary generation;
- validation and exact-input preservation;
- configurable explanation language and `No translation`;
- sentence-first Grammar;
- Conversation Practice with selectable level;
- non-blocking status messages;
- Batch / Queue import;
- Practice mode;
- Print Test with separate answer key;
- existing Anki card updates;
- Gemini, OpenAI, and Claude providers.


## Syntax check

```bash
python -m compileall src main.py main_gui.py main_gui_custom.py
```

## Automated tests

```bash
pipenv run python -m pytest -v
```

With coverage:

```bash
pipenv run python -m pytest   --cov=src   --cov-report=term-missing   --cov-report=html
```

## Manual smoke test

### Classic GUI

- application startup;
- refresh Anki decks;
- generate a valid vocabulary card;
- verify explanation-language selection;
- verify `No translation`;
- verify invalid-input warning;
- add a card to Anki;
- regenerate the same card and test existing-note update;
- Conversation Practice startup;
- verify selected conversation level.

### Modern GUI — Vocabulary and Grammar

- generate a vocabulary card;
- verify natural example and collocations;
- analyse a grammar sentence;
- save a grammar card to Anki;
- verify non-blocking success status.

### Modern GUI — Batch / Queue

- load TXT;
- load CSV;
- paste a multiline list;
- generate one item;
- test Add, Skip, Regenerate, Edit, Previous, and Next;
- verify automatic advance;
- verify counters and item states;
- save and resume a session.

### Modern GUI — Practice and Print

- load supported cards from an Anki deck;
- test All, New, Due, and Overdue filters;
- select a subset of cards;
- complete one vocabulary exercise;
- complete one grammar exercise;
- verify inline checking;
- generate test HTML;
- generate answer-key HTML;
- both files open correctly in a browser.

### Providers

For Gemini, OpenAI, and Claude:

- verify provider appears only with a configured key;
- generate vocabulary;
- analyse grammar;
- conversation start and review flow;
- verify invalid JSON and missing text are handled.

## Prompt regression cases

Keep these examples in the evaluation set:

- `thorough` — must not be forced into a sunset context;
- `short fuse` — only established collocations;
- `spontaneous` — no invented translation;
- `pizza` — natural meaning-driven example;
- `look forward to` — correct grammar and phrase handling;
- misspelled or invented words — validation failure;
- `curso de reciclaje` — professional refresher-course meaning, not literal waste recycling.

## Documentation map

| Change | Documentation |
|---|---|
| Prompt behaviour | `PROMPT_ENGINEERING_HISTORY.md` |
| Anki fields/templates | `ANKI_CARD_MODEL.md` |
| Existing-note replacement | `ANKI_UPDATE_EXISTING_CARDS.md` |
| Batch / Queue | `BATCH_QUEUE_MODE.md` |
| Practice / Print | `PRACTICE_AND_PRINT_MODE.md` |
| Claude | `CLAUDE_PROVIDER.md` |
| Module boundaries | `ARCHITECTURE.md` |
| Video narrative | `VIDEO_SCRIPT_PROMPT_ENGINEERING.md` |


## Speech tests

- provider factory registration;
- deterministic cache keys;
- cache reuse;
- provider calls with mocks;
- Anki media upload;
- existing-note Audio updates;
- missing credentials, empty text, and provider errors.


## Simple Auto Batch regression checks

- Start the modern GUI.
- Load a small list of 5 vocabulary items.
- Run `Auto-generate pending`.
- Confirm that an autosave file appears in `batch_autosaves/`.
- Run `Add all ready`.
- Confirm that cards are added one by one and the status changes after each card.
- Confirm that one duplicate does not stop the whole batch.
- Confirm that one failed card is marked as `error`.
- Confirm that `logs/ai_anki_app.log` records the operation.


## Audio debugging regression checks

- Change card language and confirm that TTS voice presets refresh.
- Generate audio for a new card and confirm a cache file is created.
- Add the card to Anki and confirm the Audio field contains `[sound:...]`.
- Force an AnkiConnect/media error and confirm the message is visible in the GUI.
- Confirm `logs/ai_anki_app.log` records the selected provider, model, voice, cache path, and error details.
- Generate audio for existing cards and confirm errors are logged per note instead of being swallowed silently.


## Auto Batch rate-limit regression checks

- Simulate or trigger a provider 429 response.
- Confirm the current item is marked `rate_limited`.
- Confirm Auto Batch stops instead of retrying the same item repeatedly.
- Confirm the autosave file is updated.
- Confirm the log contains the rate-limit stop reason.
- Confirm `Auto-generate pending` later continues only truly pending items.
