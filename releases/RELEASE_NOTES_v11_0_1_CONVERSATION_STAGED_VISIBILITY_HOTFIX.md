# v11.0.1 — Conversation staged visibility hotfix

Small UX hotfix on top of v11.0 LangSmith / LLMOps Foundation.

## Fixed

- Conversation Practice staged expressions are now visible as an explicit list before being sent to Batch / Queue.
- After sending expressions to Batch / Queue, the panel keeps a clear "Last sent to Batch / Queue" list instead of looking empty.
- Added an "Open Batch / Queue" button in the Conversation Practice panel.
- Clarified panel copy: the flow is checkbox -> edit/remove -> stage -> send to Batch / Queue. No direct Anki write happens from Conversation Practice.
- Reset now clears the staged/last-sent preview correctly.

## Why

The previous UI showed a status sentence, but the staged box could look empty or ambiguous. Users could not easily verify which expressions had been staged or sent.

## Tests

```bash
python -m py_compile src/ui/modern_gui.py
python -m compileall -q src
python -m pytest -q tests/observability/test_langsmith_tracing.py tests/ai/test_batch_grammar_prompt.py
```
