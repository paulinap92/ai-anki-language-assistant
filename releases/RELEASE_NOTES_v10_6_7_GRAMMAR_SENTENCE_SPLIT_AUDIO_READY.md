# v10.6.7 — Grammar sentence split + audio-ready import

## Why

The previous grammar merge fixed duplicate-looking candidates, but it could make
multi-example grammar material too compressed. For learning and audio, each real
source sentence should become its own grammar card candidate.

Example source material may contain one grammar rule plus several example
sentences. The app should not create one grouped card with all examples hidden
inside it. It should create one card per sentence so every sentence can become an
Anki grammar note and later receive its own TTS audio.

## Changed

- Grammar import is now sentence-first again.
- When a rule-like `Grammar target` matches one or more `Provided example` rows,
  each matching example is converted into a separate `Grammar` candidate.
- The shared grammar target/pattern is preserved on each sentence candidate.
- A rule-only candidate is removed only when sentence candidates were created
  from it, so the UI avoids duplicate rule cards while keeping one card per
  readable sentence.
- Batch grammar prompt now understands the review format:

```text
grammar target | source sentence
```

and tells the model to put only the source sentence into the Anki `Sentence`
field. This keeps grammar cards audio-ready: the sentence field is clean and can
be read by the Speech / Audio workflow.

## Example

Before v10.6.7, related examples could be merged too much.

Now:

```text
Grammar target
Target: should have / ought to have + past participle
Example: We should have / ought to have driven – it would have been quicker.

Grammar target
Target: should have / ought to have + past participle
Example: I should have called you earlier.
```

Each sentence is sent to Batch / Queue as its own grammar row.

## Validation

- `python -m py_compile src/ui/modern_gui.py src/ai/prompts.py`
- `python -m compileall -q src`
- `python -m pytest -q tests/ai/test_batch_grammar_prompt.py`

Full `pytest -q` still cannot run in this sandbox because optional provider SDKs
are not installed here: `anthropic` and `google genai`.
