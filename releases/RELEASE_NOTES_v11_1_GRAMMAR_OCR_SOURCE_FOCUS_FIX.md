# v11.1 — Grammar OCR / Source Focus Fix

This release focuses on quality cleanup for grammar cards generated from OCR / Import Material.

## Fixed / improved

- Strengthened the Batch grammar prompt so OCR-imported grammar rows keep the exact source focus.
- For rows in the form `grammar target | source sentence`:
  - the right side must become the `sentence` field and audio/readable sentence;
  - the left side must stay visible in `structure`;
  - textbook rules or abstract headings must not become the audio sentence.
- Added explicit prompt rules for concrete grammar targets and word-form transformations, for example:
  - `used to + base verb`,
  - `Can I + base verb`,
  - `should have + past participle`,
  - `un hippi -> hippies`.
- Added a deterministic post-generation guard for Batch grammar cards:
  - restores the exact OCR source sentence as the grammar `sentence` when provided;
  - restores the source grammar target in `structure` when the provider hides/replaces it;
  - warns when a generated grammar sentence looks like an abstract topic label instead of an example using the target;
  - keeps source rules/notes as usage notes, not as audio sentences.
- Batch grammar previews now show source-focus warnings, the source grammar target, and the source sentence/audio target when available.

## Why

Some OCR-generated grammar cards were visually nice but taught the wrong thing. Examples:

- source target `un hippi -> hippies` became a card about `de + adjective/noun`;
- source target `used to + base verb` was buried under the large title `repeated actions in the past`;
- source example sentences and source rules could be mapped to the wrong fields.

v11.1 narrows the fix to the key rule:

```text
structure / source target = grammar focus
source sentence = sentence/audio
rule / explanation = note
```

## Tests

Passed:

```bash
python -m py_compile src/ui/modern_gui.py src/ai/prompts.py
python -m compileall -q src
python -m pytest -q tests/ai/test_batch_grammar_prompt.py tests/ai/test_grammar_source_focus_guard.py tests/observability/test_langsmith_tracing.py
```

`test_grammar_source_focus_guard.py` is skipped when `customtkinter` is not installed in the test environment.
