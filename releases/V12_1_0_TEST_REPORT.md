# v12.1.0 Test Report

## Validation completed

- `python -m compileall -q src main.py main_gui.py main_gui_custom.py main_gui_custom_private.py` — passed.
- Targeted regression suite for Batch duplicate handling, v12.1 CSV parsing, Import HTML/text, vocabulary extraction prompts, Conversation export/audio and flashcard prompts — **29 passed**.
- Broader suite excluding unavailable optional Claude/Gemini SDK tests — **103 passed, 2 skipped, 3 failed**.

## Known pre-existing failures

The same three failures reproduce unchanged on the v12.0.9 clean package:

1. `test_batch_grammar_prompt_contains_structure_and_topic_variety_rules`
2. `test_validator_blocks_spanish_verb_example_that_uses_synonym` (`derrumbar(se)` validator case)
3. `test_smart_grammar_import_prompt_routes_rules_examples_transformations_and_exercises`

They are not introduced by v12.1.0.

## Environment limitation

The complete provider test collection cannot be collected in this sandbox because optional provider SDKs are unavailable (`anthropic` and `google.genai`). Windows GUI rendering, AnkiConnect and live TTS/provider behavior still require real local testing.
