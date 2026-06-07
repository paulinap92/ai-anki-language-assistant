# Development Notes

## What changed in the cleanup

- The original working flow was preserved.
- Large mixed modules were split into responsibility-based packages.
- Anki templates were moved out of the API client.
- Anki field rendering was moved to a dedicated builder.
- AI clients were grouped under `src/ai`.
- Domain models and language utilities were moved under `src/domain`.
- GUI files were moved under `src/ui`.
- Legacy compatibility wrapper modules were removed.
- The real `.env` file was removed from the deliverable package.

## Recommended workflow for future changes

1. Make one small change.
2. Run syntax checks.
3. Start the GUI.
4. Test one flashcard generation.
5. Test adding one card to Anki.
6. Test conversation practice.
7. Commit.

## Syntax check

```bash
python -m compileall src main.py main_gui.py main_gui_custom.py
```

## Manual smoke test

1. Open Anki.
2. Start the stable GUI:

```bash
python main_gui.py
```

3. Refresh decks.
4. Generate one card.
5. Add it to a test deck.
6. Start a conversation topic.
7. Send one answer.
8. Select all suggested expressions.
9. Add them to Anki.

## Where to add new code

| Change | Location |
|---|---|
| New AI provider | `src/ai/providers/` |
| New prompt | `src/ai/prompts.py` |
| New card field | `src/domain/models.py`, `src/anki/templates.py`, `src/anki/field_builder.py` |
| New supported language | `src/domain/languages.py` |
| GUI change | `src/ui/classic_gui.py` or `src/ui/modern_gui.py` |
| CLI change | `src/cli/app.py` |

## Do not commit secrets

Never commit `.env`. Only `.env.example` belongs in the repository.
