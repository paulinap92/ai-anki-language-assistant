# LangSmith / LLMOps Test Matrix

Use this matrix when validating the LangSmith/LLMOps integration. The goal is not to test every UI branch every day, but to confirm that the app traces the full AI-card pipeline:

`generation → validation → human review → audio consistency → Anki outcome`.

## Smoke test

| ID | Area | User action | Expected trace | Provider | Expected metadata | Expected outcome | LangSmith result | App result | Pass/Fail | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| LS-01 | LLMOps | Click `Test trace` | `llmops_test_trace` | system | `feature`, `source`, `outcome`, `latency_ms` | `generated` / `test` |  |  |  |  |
| LS-02 | Vocabulary | Generate `short fuse` | `vocabulary_card_generation` | Gemini / Claude / OpenAI | `provider`, `model`, `source`, `prompt_version`, `latency_ms` | `generated` |  |  |  |  |
| LS-03 | Vocabulary phrase | Generate `to have it out with sb` | `vocabulary_card_generation` | Gemini / Claude / OpenAI | `card_type`, `validation_passed`, `red_flags_count` | `generated` |  |  |  |  |
| LS-04 | Invalid input | Generate `asdfgh banana roofly` | `vocabulary_card_generation` | Gemini / Claude / OpenAI | `validation_passed=false`, `issue_type` | `validation_warning` / `invalid_input` |  |  |  |  |
| LS-05 | Grammar | Analyze `Can I + base verb...?` | `grammar_analysis` / `grammar_card_generation` | Gemini / Claude / OpenAI | `card_type=grammar`, `source=grammar_tab` | `generated` |  |  |  |  |

## Import / Batch / Review

| ID | Area | User action | Expected trace | Provider | Expected metadata | Expected outcome | LangSmith result | App result | Pass/Fail | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| LS-06 | Import Material | Find candidates from OCR/text with AI | `import_candidate_generation` | Gemini / Claude / OpenAI | `extraction_mode`, `candidate_count`, `candidate_type_counts` | `candidate_generated` |  |  |  |  |
| LS-07 | Smart grammar import | Import discourse markers / grammar rules | `smart_grammar_import` | Gemini / Claude / OpenAI | `source_type_counts`, `grammar_candidates` | `candidate_generated` |  |  |  |  |
| LS-08 | Conversation | Get conversation feedback | `conversation_feedback` | Gemini / Claude / OpenAI | `improvement_level`, `feedback_language`, `provider`, `model` | `generated` |  |  |  |  |
| LS-09 | Batch | Generate one batch item | `batch_item_generation` | Gemini / Claude / OpenAI | `batch_item_index`, `batch_size`, `source=batch_queue` | `generated` |  |  |  |  |
| LS-10 | Batch summary | Finish auto-generation | `batch_generation_summary` | system | `status_counts`, `ready_count`, `failed_count`, `invalid_count` | `completed` |  |  |  |  |
| LS-11 | Review | Click Add to Anki | `anki_add_outcome` | system | `outcome=added_to_anki`, `card_type` | `added_to_anki` |  |  |  |  |
| LS-12 | Duplicate | Try adding duplicate card | `duplicate_detection` | system | `duplicate_detected=true` / `outcome=duplicate_skipped` | `duplicate_skipped` / `updated_existing_note` |  |  |  |  |
| LS-13 | Update | Update existing note | `anki_update_outcome` | system | `updated_existing_note=true` | `updated_existing_note` |  |  |  |  |

## Audio quality and Anki audio export

| ID | Area | User action | Expected trace | Provider | Expected metadata | Expected outcome | LangSmith result | App result | Pass/Fail | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| LS-A01 | Audio sentence selection | Generate audio for vocabulary card `short fuse` | `audio_sentence_selection` | TTS/system | `card_type=vocabulary`, `audio_sentence_present=true`, `audio_sentence_len` | `selected` |  |  |  |  |
| LS-A02 | Audio alignment | Generate audio for a grammar card with visible sentence | `audio_sentence_alignment_check` | system | `alignment_passed=true`, `card_type=grammar/existing_card_audio` | `passed` |  |  |  |  |
| LS-A03 | Audio alignment guard | Select a source field that differs from visible grammar sentence | `audio_sentence_alignment_check` | system | `alignment_passed=false`, `issue_type=audio_sentence_mismatch` | `blocked` |  |  |  |  |
| LS-A04 | TTS generation | Generate one audio file | `tts_generation` | TTS provider | `tts_provider`, `tts_model`, `voice`, `cache_hit`, `latency_ms` | `audio_generated` / `cache_hit` |  |  |  |  |
| LS-A05 | Audio cache | Generate the same audio twice | `audio_cache_outcome` | system | `cache_hit=false` then `cache_hit=true`, `audio_file_exists=true` | `cache_miss` / `cache_hit` |  |  |  |  |
| LS-A06 | Anki audio | Add card with generated audio to Anki | `audio_attach_to_anki` | system | `audio_attached=true`, `anki_media_file`, `target_audio_field` | `attached_to_anki` / `media_stored` |  |  |  |  |

## Model comparison results

| Test case | Provider | Model | Feature | Latency | Validation passed | Red flags | Accepted by user | Added to Anki | Notes |
|---|---|---|---|---:|---|---:|---|---|---|
| short fuse | Gemini | gemini-2.5-flash | vocabulary |  |  |  |  |  |  |
| short fuse | Claude |  | vocabulary |  |  |  |  |  |  |
| short fuse | OpenAI |  | vocabulary |  |  |  |  |  |  |
| to have it out with sb | Gemini | gemini-2.5-flash | vocabulary phrase |  |  |  |  |  |  |
| Can I + base verb | Gemini | gemini-2.5-flash | grammar |  |  |  |  |  |  |
| On the other hand | Gemini | gemini-2.5-flash | grammar/discourse |  |  |  |  |  |  |

## Card quality evaluation

| ID | Input | Card type | Expected focus | Actual focus | Example natural? | Exact target preserved? | Translation OK? | Source focus OK? | Audio/sentence alignment OK? | Decision | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CQ-01 | short fuse | vocabulary | idiom: gets angry quickly |  |  |  |  | N/A | N/A |  |  |
| CQ-02 | to have it out with sb | vocabulary phrase | resolve problem by direct discussion/argument |  |  |  |  | N/A | N/A |  |  |
| CQ-03 | asdfgh banana roofly | invalid | validation warning |  | N/A | N/A | N/A | N/A | N/A |  |  |
| CQ-04 | Can I + base verb...? | grammar | permission structure |  |  |  | N/A |  |  |  |  |
| CQ-05 | On the other hand | discourse marker | contrasting point |  |  |  | N/A |  |  |  |  |
