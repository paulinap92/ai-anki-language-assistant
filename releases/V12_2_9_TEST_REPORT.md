# v12.2.9 Test Report

## Focused regression tests

- Import Material typed Queue / mixed routing
- Candidate Review guardrails, filters and pagination
- v12.2.9 educational priority logic
- source-size / analysis-part guardrails
- Smart Vocabulary prompt contract
- content-driven candidate count contract
- Smart Grammar import prompt contract

Result: **32 focused tests passed**.

## Broader suite

Run with optional Claude/Gemini SDK-specific test modules excluded because those SDKs are not installed in the build environment.

Result: **163 passed, 2 skipped, 2 failed**.

The same two failures are reproducible on the untouched v12.2.8 package and are unrelated to v12.2.9:

1. `test_batch_grammar_prompt_contains_structure_and_topic_variety_rules`
2. `test_validator_blocks_spanish_verb_example_that_uses_synonym`

## Compile check

`python -m compileall -q src tests` passed.
