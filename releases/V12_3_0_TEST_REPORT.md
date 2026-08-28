# v12.3.0 Test Report

## New voice-library regression tests

- Piper online catalog parsing and language filtering
- Piper preview/model/config URL construction
- Local Piper `.onnx` + `.onnx.json` import validation
- Installed Piper voice discovery and metadata labels
- ElevenLabs shared Voice Library parsing
- ElevenLabs shared-voice add endpoint handling
- ElevenLabs My Voices parsing
- Local non-secret ElevenLabs voice registry persistence

Result: `6 passed` in `tests/speech/test_voice_library.py`.

## Broader regression set

`pytest -q tests/speech tests/core tests/ui`

Result: `81 passed`.

`python -m compileall -q src tests`

Result: passed.

Full available suite excluding unavailable optional Claude/Gemini SDK collection tests:

`169 passed, 2 skipped, 2 failed`.

The same two failures reproduce on the untouched v12.2.9 package and are unrelated to v12.3.0:

- `test_batch_grammar_prompt_contains_structure_and_topic_variety_rules`
- `test_validator_blocks_spanish_verb_example_that_uses_synonym`

The environment used for packaging does not have the optional `anthropic` and `google.genai` SDKs, so the corresponding provider tests cannot be collected here.
