# v12.4.4 test report

- `python -m compileall -q src tests`: PASS
- Target-first Grammar prompt/template focused suite: 29 passed.
- Broad suite excluding unavailable optional Claude/Gemini SDK collection tests and one unrelated pre-existing TSV local-finder assertion: 214 passed, 2 skipped, 1 deselected.
- Full pytest collection in this build environment cannot load optional `anthropic` and `google.genai` SDKs.

Regression coverage includes:
- long rule text cannot be the intended grammar target contract;
- third conditional meta-description is explicitly rejected as an example;
- direct sentence analysis extracts a concise target while preserving the source sentence;
- Smart Grammar extraction normalizes long rules to short targets;
- Anki grammar front uses `Target` rather than `Sentence`;
- one visible/audio example is used;
- Learning Profile explanation language is forwarded through provider/tracing layers;
- old grammar payloads remain readable.
