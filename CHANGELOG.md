## v12.0.5 - Conversation feedback and STT quality

- Fixed clipped Conversation Batch / Queue buttons by stacking full-width actions.
- Added compact coaching by default with optional Detailed coaching for corrected/stronger answers and mini practice.
- Kept tutor replies conversational and brief instead of drifting into long domain lectures or overconfident specialist advice.
- Separated genuine errors, naturalness improvements and probable speech-transcription errors.
- Added context-aware faster-whisper transcription using the selected conversation language, topic, active flashcards, speaking cues and recent context.
- Enabled Whisper VAD and disabled cross-segment previous-text conditioning to reduce cutoffs and hallucinated carry-over.
- Changed the clean-install Whisper default from `base` to `small`; existing explicit `.env` choices remain unchanged.

## v12.0.4 — Conversation UX, card rotation and coverage


- Made the entire right Conversation panel vertically scrollable so staged items and session controls remain reachable on smaller windows.
- Moved speaking cues and new-card candidates above the staged queue; session flashcards are now collapsed at the bottom by default.
- Added per-turn accumulation of genuinely new flashcard candidates, capped at 0–3 new items per exchange, with clear/stage controls and disabled staging buttons when nothing new exists.
- Added persistent per-deck card selection modes: Continue rotation, Anki due cards, Random cards and Repeat last session.
- Continue rotation avoids repeating cards until the current shuffled cycle is exhausted; Reset keeps rotation progress.
- Added read-only due-card lookup through AnkiConnect without changing the active generation deck or Anki scheduling state.
- Added session coverage tracking with a live `x/30 practised` counter and used/not-used markers.
- Flashcard context now prioritizes targets not used yet and tells the tutor not to base consecutive questions on the same target unless clarification is needed.
- Added regression tests for rotation, due-card lookup and updated flashcard conversation prompts.

## v12.0.3 — Conversation suggestion separation

- Kept `Talk about a topic` suggestions unchanged.
- Split flashcard-based Conversation into three explicit concepts: session flashcards, expressions to use next, and genuinely new flashcard candidates.
- Existing deck targets are no longer offered as new cards, including case, punctuation and article-only variants.
- Longer useful collocations such as `impartir una clase magistral` remain valid even when `clase magistral` already exists.
- New-card candidates must be grounded in the current learner answer, correction, improved answer, mini-practice or tutor reply; unrelated prompt-seeded expressions are rejected.
- Added normalized duplicate filtering against the full selected Anki deck, the current session and already staged expressions.
- Added separate right-panel sections and regression tests for the new workflow.

## v12.0 — Flashcard-based Conversation

- Added a second Conversation Practice mode: `Talk based on flashcards`.
- Uses the current in-memory Batch / Queue cards without AnkiConnect.
- Generated vocabulary/grammar cards provide meanings, examples and usage; pending rows provide targets and source sentences.
- Reuses flashcard context on every feedback turn and prioritizes target expressions in suggestions.
- Limits one session to 30 usable items and skips failed/invalid/skipped Batch rows.
- Added prompt, context-building and regression tests.

## v11.5.11 — Separate Vision OCR from Image Candidate Extraction

- OpenAI/Gemini Vision OCR now transcribes image/PDF material into the reviewed text box only.
- Vision OCR no longer creates candidate drafts, Batch rows, grammar analyses or direct imports.
- Added a strict multimodal OCR prompt that preserves visible text, headings, bullets and tables while forbidding JSON/candidate generation.
- Candidate extraction remains a separate explicit `Find candidates with selected strategy` step after the user reviews/cleans OCR text.
- Direct image-to-candidate extraction is kept as an advanced compatibility helper, but it is no longer the normal OCR button path.

## v11.5.10 — UI and Import Interaction Fixes

- Screenshot/image staging is now passive; loading or pasting a screenshot no longer auto-runs OCR or multimodal import.
- Import Material text/candidate panels and Batch preview reset scroll position after repeated actions so new results are visible immediately.
- Added a Batch `Remove item` action with debounced autosave for faster repeated deletes.
- Status messages now distinguish loaded/staged sources from explicit OCR/API calls.

## v11.5.9 — Workflow-specific model selection

- Added workflow-specific model roles for card generation, Import/OCR extraction, multimodal import, and review/fix workflows.
- Import Material text candidate extraction now uses the configured import model instead of always using the normal card-generation model.
- Multimodal import now passes the configured multimodal model explicitly.
- LangSmith traces include `workflow_model_role` to make model/cost comparison clearer.


## v11.5 — Multimodal Import Extraction

- Added OpenAI/Gemini multimodal import methods for screenshot/book-photo/table extraction.
- Added table-aware candidate extraction mapping Expression → target, Example → sentence/audio, Use → source note.
- Added highlighted/marked item extraction rules for physical-book workflows.
- Added `OPENAI_MULTIMODAL_MODEL` and `GEMINI_MULTIMODAL_MODEL` env options.

# Changelog

## v12.0.2 — Conversation meaning and continuity

- Added a dedicated target-language `tutor_reply` before the next question.
- Direct learner questions and unknown flashcards are now answered before the conversation moves on.
- Conversation feedback receives recent turn history instead of treating every answer as an isolated exchange.
- Generic Anki `Front`/`Back` notes preserve `Back` as authoritative card content instead of mislabelling it as an example sentence.
- Flashcard explanations must use the card meaning, definition, back, example or usage and avoid confident invention.
- Added regression tests for Basic cards, explain-on-demand behaviour and history-aware prompts.

## v12.0.1 — Conversation deck source selector

- Flashcard conversation now defaults to a selected Anki deck.
- Added visible Flashcard source and Deck selectors inside Conversation Practice.
- Added Refresh decks and Current Batch / Queue as an optional secondary source.
- Reads vocabulary, grammar, and recognizable legacy notes without changing the card-generation deck.

This file keeps version history out of the main README. Detailed notes live in `releases/`.

## Current project line

### v11.5.12 — Audio Metadata Fields

Stored hidden TTS provider/model/voice/source metadata on Anki notes for new audio generation, Fix Cards audio repair and existing-card audio backfill.

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
