# v8.1.5.5 — Batch UI, grammar audio, and provided examples

## Changed

- Cleaned up Batch / Queue controls into clearer sections.
- Hid Batch problem navigation when there are no problems.
- Fixed a runtime UI construction issue in the Batch `Edit card` button.
- Strengthened topic/context instructions to avoid repetitive topic wording such as `ensayo` in every example.
- Added `Provided examples` Batch mode for `target | sentence` input.
- Added `SENTENCE_BASED_CARD_PROMPT_VERSION = v1-provided-example-card`.
- Added provider method `generate_sentence_card(...)` for Gemini/OpenAI/Claude.
- Added grammar audio support:
  - `AI Grammar Light Card` now includes `Audio` and `ExampleAudio` fields.
  - grammar card templates render audio under the natural context example.
  - grammar card audio backfill can use `ContextExample` as source text.
  - existing grammar note types are updated idempotently before audio scan.
- Added card type tags for Batch-generated cards:
  - `card_type::vocabulary`
  - `card_type::grammar`
  - `card_type::provided_example`

## Tests

- `python -m compileall -q src tests`
- `pytest -q tests/ai/test_batch_grammar_prompt.py tests/ai/test_prompt_quality_validation.py tests/ai/test_prompts_topics.py tests/anki tests/speech`

Result: 38 passed.

Full `pytest -q` still requires optional provider SDKs in this environment: `anthropic` and `google.genai`.
