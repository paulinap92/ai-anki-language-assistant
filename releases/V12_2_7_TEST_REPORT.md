# v12.2.7 test report

## Passed

- `python -m compileall -q src tests`
- `pytest -q tests/ui tests/ocr tests/conversation tests/speech tests/anki tests/core` → **99 passed**
- focused import/prompt regression set → **10 passed, 1 skipped**
- new v12.2.7 guardrail/review tests are included in the UI suite.

## Known pre-existing AI-suite issues

The full `tests/ai` collection cannot run in this environment because optional cloud SDKs `anthropic` and `google.genai` are not installed. Excluding those modules still exposes two failures that were reproduced unchanged on the untouched v12.2.6 package:

1. `test_batch_grammar_prompt_contains_structure_and_topic_variety_rules`
2. `test_validator_blocks_spanish_verb_example_that_uses_synonym`

Neither failure was introduced by v12.2.7.
