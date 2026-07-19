# v8.1.4.3 — Example / Audio / Batch Sanity Hotfix

Focus: fix real issues found during daily use instead of adding new features.

## Changes

- Strengthened vocabulary prompt to require that the example sentence uses the target word/phrase itself or a valid inflected/conjugated form.
- Added local Spanish verb example validation for cases such as:
  - `derrumbar(se)` using `derribó` instead of `derrumbó / se derrumbó`,
  - `enfurecer(se)` using `endurecieron` instead of `enfureció / enfurecieron`,
  - `encolerizarse` using `encolorizó` instead of `encolerizó`.
- Normalized outer quotation marks for provider exact-input checks so phrase prompts such as `"Nevertheless…"` do not fail when the provider returns `Nevertheless…`.
- Improved Batch final summary: it now reports the whole queue, not only the `ready` cards processed by `Add all ready`.
- Batch final summary now includes examples of failed and invalid/blocked items when available.
- After Add all finishes, the current word field changes to `Batch completed` instead of leaving the last word visible.
- Added `Test TTS provider` button in Speech / Audio.
- Added TTS preflight before audio batch: if provider diagnostics fail, batch does not start.
- ElevenLabs diagnostics now distinguish missing API key from provider HTTP failures such as `401 Unauthorized`.

## Not changed

- No OCR/STT/LangGraph work.
- No full language-neutral schema migration yet.
- No full Spanish conjugation engine; validation is intentionally lightweight and conservative.
