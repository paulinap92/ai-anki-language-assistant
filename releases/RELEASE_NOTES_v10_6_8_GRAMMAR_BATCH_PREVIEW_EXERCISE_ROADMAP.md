# v10.6.8 Grammar Batch Preview + Exercise OCR Roadmap

## Fixed

- Batch preview no longer labels pending Grammar items as `WORD / PHRASE`.
- Pending Grammar rows now show separate fields:
  - `GRAMMAR TARGET`
  - `SENTENCE TO READ`
  - optional `SOURCE RULE / NOTE`
- Import Material → Batch now avoids sending long textbook rule explanations as the sentence/audio target.
- If an OCR grammar candidate has `target | rule explanation`, Batch keeps the target and stores the explanation as a source note.
- If an OCR grammar candidate has `target | real sentence`, Batch keeps both and displays them clearly.
- If the target itself is actually a sentence, Batch prefers the readable sentence as the audio-ready grammar input.

## Prompt update

- Batch Grammar prompt now asks the model to create a natural example sentence when the input is only a grammar pattern.
- This keeps generated Grammar cards audio-ready instead of storing patterns such as `aunque + subjuntivo` in the `sentence` field.

## Future plan saved

Added `docs/FUTURE_PLANS.md` section:

- `Grammar Exercise OCR Mode — future feature`
- planned flow for OCR screenshots of textbook gap-fill / multiple-choice grammar exercises
- exercise drafts with user-filled or AI-solved answers
- reviewed completed sentence → one Grammar card → one audio sentence

## Validation

Passed:

```bash
python -m py_compile src/ui/modern_gui.py src/ai/prompts.py
python -m compileall -q src
python -m pytest -q tests/ai/test_batch_grammar_prompt.py
```
