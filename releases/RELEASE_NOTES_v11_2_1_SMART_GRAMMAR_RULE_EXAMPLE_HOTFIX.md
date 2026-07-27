# v11.2.1 — Smart Grammar Rule Example Hotfix

Small hotfix on top of v11.2 Smart Grammar Import / Mixed Source Mode.

## Problem

Some OCR grammar pages contain rule-only lines, for example:

```text
have with this meaning is a stative (non-action) verb and is not used in continuous tenses.
```

The AI could incorrectly classify these as `structure_sentence` and put the textbook rule into the candidate `Example` field. This later made weak grammar cards where the audio/example was a rule instead of a natural sentence.

## Changes

- Expanded rule/explanation detection for textbook grammar lines:
  - `stative`, `dynamic`, `continuous tenses`, `main verb`, `auxiliary verb`, `obligation`, `possession`, etc.
- If a grammar candidate is marked as `structure_sentence` but the sentence is actually a rule, the app downgrades it to:
  - `source_type = rule`
  - `strategy = generated_example_from_rule`
  - `source_rule = original rule`
  - empty `sentence`, so Batch can generate a natural example.
- Candidate preview now uses clearer labels:
  - `Grammar focus`
  - `Example / audio`
  - `Source sentence`
- Rule-only grammar candidates show:

```text
Example / audio: AI will generate a natural example in Batch
```

instead of pretending the source rule is an example.

## UX cleanup

The AI extraction section now says `AI import strategy` and explains that Smart grammar import should be used for grammar pages with rules + examples.

## Tests

```bash
python -m py_compile src/ui/modern_gui.py src/ai/prompts.py
python -m compileall -q src
python -m pytest -q tests/ai/test_smart_grammar_rule_example_guard.py tests/ai/test_smart_grammar_import_prompt.py tests/ai/test_batch_grammar_prompt.py tests/observability/test_langsmith_tracing.py
```

Note: tests depending on `customtkinter` may be skipped if the package is not installed in the test environment.
