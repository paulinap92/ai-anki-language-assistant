# v11.3.3 — LLMOps Audio, Import and Review Traces

This release expands LangSmith/LLMOps observability beyond core model calls.

## Added traces

- `import_candidate_generation` for AI candidate extraction from OCR/imported material
- `smart_grammar_import` for mixed grammar source import and source-type statistics
- `batch_item_generation` for Batch/Queue item generation outcomes
- `batch_generation_summary` for auto-generation summaries
- `card_review_outcome`, `anki_add_outcome`, `anki_update_outcome`, and `duplicate_detection` for human review and Anki export decisions
- `audio_sentence_selection` and `audio_sentence_alignment_check` to prevent visible sentence/audio sentence mismatch
- `tts_generation` and `audio_cache_outcome` for TTS latency and cache behaviour
- `audio_attach_to_anki` for audio media export to Anki

## Changed

- User/Anki outcome events now go to LangSmith as non-LLM quality traces instead of only the local LLMOps log.
- `.env.example` uses the EU LangSmith endpoint by default for EU workspaces.
- Added `docs/LLMOPS_TEST_MATRIX.md` with smoke, import, batch, review, audio and model comparison test tables.

## Goal

The tracked flow is now:

`generation → validation → human review → audio consistency → Anki outcome`
