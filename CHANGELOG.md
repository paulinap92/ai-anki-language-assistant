
## v11.5 — Multimodal Import Extraction

- Added OpenAI/Gemini multimodal import methods for screenshot/book-photo/table extraction.
- Added table-aware candidate extraction mapping Expression → target, Example → sentence/audio, Use → source note.
- Added highlighted/marked item extraction rules for physical-book workflows.
- Added `OPENAI_MULTIMODAL_MODEL` and `GEMINI_MULTIMODAL_MODEL` env options.

# Changelog

This file keeps version history out of the main README. Detailed notes live in `releases/`.

## Current project line

### v11.3.3 — LLMOps Audio, Import and Review Traces

Expanded LangSmith/LLMOps observability beyond core model calls: import, smart grammar import, Batch, review outcomes, Anki outcomes, audio alignment, TTS, audio cache and audio export traces.

### v11.3 — LangSmith Quality Metrics

Added quality metadata such as validation status, red-flag count, issue type, outcome, feature/source and prompt-version metadata.

### v11.2 — Smart Grammar Import / Mixed Source Mode

Added AI classification of grammar OCR fragments and routing strategies for structure + sentence, rule-only material, transformations, exercises and sentence-only input.

### v11.1 — Grammar OCR / Source Focus Fix

Protected grammar source focus: structure stays as grammar focus, source sentence stays as sentence/audio, and rules stay as notes.

## OCR / Import and candidate flow

### v10.6.8 — Grammar Batch Preview + Exercise OCR Roadmap

Improved pending Grammar Batch preview and saved the future Grammar Exercise OCR Mode roadmap.

### v10.6.7 — Grammar sentence split + audio-ready import

Made grammar import sentence-first again so each real source sentence can become its own audio-ready grammar card.

### v10.5 — Import UX + Suggestions Queue Fix

Cleaned Import Material and Conversation suggested-expression flows so reviewed candidates go through Batch / Queue instead of direct Anki writes.

### v10.3 — Candidate Flow Trial

Added editable candidate drafts, cherry-pick flow and safer Batch item editing.

## OCR and STT milestones

### v9.1.9 — Conversation STT trial

Added a small local Whisper/faster-whisper speech-to-text trial for Conversation Practice.

### v9.1 — OCR manual picker + Mistral auto candidates

Added explicit local OCR manual picker and Mistral OCR auto-candidate workflows.

## Batch, audio and validation stabilization

### v8.1.5.x — Validation, language-neutral defaults and audio scope fixes

Stabilized Batch validation, warning overrides, language-neutral schemas/defaults, audio deck/language scope and warning single-source-of-truth behavior.

### v8.1.4 — Prompt quality and validation

Added prompt-quality validation, provider self-check fields and local card quality warnings.

### v8.1.3.x — Fix Cards and audio repair hotfixes

Improved Fix Cards visibility, audio repair and existing-note update behavior.

### v8.0 — Batch Controls and Quality Stabilization

Added Pause/Stop controls, draft review, Batch card editor, better quota handling and audio resume improvements.

## Earlier stabilization

### v7.4 — No Autocall, Rate-Limit Stop, Audio Resume

Prevented silent Batch provider calls, stopped Auto Batch on rate limits and improved audio resume behavior.

For complete historical detail, see the individual files in `releases/`.
