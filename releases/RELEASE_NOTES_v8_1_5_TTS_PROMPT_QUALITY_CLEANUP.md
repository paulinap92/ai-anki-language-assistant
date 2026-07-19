# v8.1.5 — TTS + Prompt Quality Cleanup

Focus: stabilize TTS diagnostics and improve flashcard quality validation before starting OCR.

## TTS cleanup

- Added a shared `SpeechService.diagnose_provider(...)` preflight path.
- `Test TTS provider` now reports a compact diagnostic summary:
  - provider,
  - API key status,
  - auth/generation status,
  - model,
  - voice,
  - generated sample path when successful.
- Audio batch uses the same diagnostic path before starting long generation.
- If the selected TTS provider fails diagnostics, audio batch does not start.
- ElevenLabs failures now include a clearer action message: check `ELEVENLABS_API_KEY`, verify selected voice/model, or switch provider.
- Rapid audio progress updates stay inside the Speech / Audio status instead of flooding the global activity footer.
- Fatal audio stop messages now include provider, error/status, stopped item, updated/failed/skipped counts, and progress-save confirmation.

## Prompt quality cleanup

- Updated vocabulary prompt version to `v7-natural-target-usage`.
- Strengthened example rules:
  - the example must use the target item itself or a valid inflected/conjugated form,
  - it must not replace the target with a synonym, near-synonym, typo, or visually similar word,
  - it must use a natural, realistic collocation.
- Added JSON self-check fields:
  - `used_form_in_example`,
  - `example_uses_target`,
  - `collocation_naturalness`,
  - `translation_naturalness`.

## Validator cleanup

- Replaced the Spanish-specific example validator with a language-neutral lexical-anchor validator.
- Added warnings for cases where the example does not use the target item.
- Added naturalness regression checks for real user cases:
  - `come across rain`,
  - `mesmerizing flow of the smoothie`,
  - `wear down doubts`,
  - literal Polish translation like `zmęczyć jego wątpliwości`.
- Provider self-checks for `collocation_naturalness=bad` and `translation_naturalness=bad` become hard warnings.
- Existing Polish diacritic sanity remains: Polish characters such as `ą ć ę ł ń ó ś ź ż` are valid in Polish fields.

## Tests

- `python -m compileall src tests` passed.
- `pytest -q tests/ai/test_prompt_quality_validation.py tests/ai/test_prompts_topics.py tests/anki tests/speech` passed: 30 tests.
- Full `pytest -q` still cannot run in this environment because optional provider dependencies are missing: `anthropic` and `google.genai`.
