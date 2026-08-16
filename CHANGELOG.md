# v12.2.0 — Local / Hybrid / BYOK user setup

- Added a first-run Setup tab with Fully local, Hybrid / BYOK and API / BYOK profiles.
- The GUI can now open with no configured AI provider instead of failing before startup.
- Added safe starter/import/reload `.env` workflows and an Ollama reachability/model check.
- Added profile-aware provider routing and lazy cloud SDK imports so local-only installs do not require cloud AI packages.
- Added `requirements-local.txt` and `requirements-hybrid.txt`, while keeping `requirements.txt` as the full install alias.
- Import Material now shows only locally available or configured cloud OCR methods for the selected profile.
- Updated user-facing setup/privacy documentation for early distribution.

# v12.1.1 — Import Material UX simplification

- Renamed all user-facing `Batch / Queue` wording to simply `Batch`.
- Reduced Import Material from seven implementation-oriented extraction strategies to four product-facing choices: `Vocabulary & expressions`, `Grammar`, `Examples / sentences`, and `Auto`.
- Kept the mature legacy extraction contracts internally for compatibility: Vocabulary & expressions preserves useful source context, Grammar uses smart grammar routing, Examples / sentences preserves exact source pairs, and Auto uses mixed classification.
- Added short in-UI explanations for each Import mode and made AI extraction the primary path, with the local finder presented as an optional fallback.
- Simplified candidate-review wording and Batch handoff labels.

## v12.1.0 - Workflow UI cleanup and in-app voice lab

- Merged the old Single flashcard and Grammar tabs into one `Create Card` workspace with a clear Vocabulary / Grammar selector and mode-specific preview.
- Reordered Batch so the user chooses `Vocabulary`, `Grammar`, `Mixed`, or `Provided examples` before loading clean TXT/CSV/pasted input.
- Added visible Batch guidance explaining that Batch is the fast path for already-clean structured rows, while Import Material is for lessons, HTML, PDFs, screenshots, scans and mixed/raw sources.
- Made clean CSV parsing mode-aware: Provided examples and Grammar preserve column 1 as target and column 2 as sentence instead of silently discarding the second column.
- Clarified Import Material routing: TXT/HTML are forced through local text extraction with no OCR/API call for text extraction; image/scan/PDF sources use the selected OCR/vision path before candidate extraction.
- Restored a dedicated Speech / Audio `Voice Lab` with editable sample text, Play voice, Stop and Test provider controls.
- Voice/sample previews and Fix Cards audio previews now play inside the application through the shared internal audio player instead of opening the operating-system media player.
- Added friendly Import Material provider-error handling for 429/timeouts/5xx (including OpenAI/Cloudflare 520), preserving the current source/candidates, automatically retrying up to two times, and exposing `Retry last AI extraction` instead of dumping raw provider payloads into the UI.
- Simplified crowded Batch current-card actions into two rows and renamed the observability tab to `Advanced / LLMOps`.

## v12.0.9 - Batch vocabulary duplicate target consistency

- Fixed a Batch regression where a vocabulary row containing `target | source sentence` could pass the duplicate check before generation and only be reported as duplicate after AI generation.
- Vocabulary duplicate detection now has one canonical key: the learner's target word/phrase compared with Anki's `Word` field.
- Source/example sentences are never part of the vocabulary duplicate key.
- Imported Vocabulary + source example rows prefer their stored `provided_target`; pipe/TAB rows use only the left-side target.
- The exact same original target is reused for pre-generation duplicate checks, Add-all duplicate summaries and the final Anki add/update decision.
- Sentence-only Provided Examples intentionally skip pre-generation Word lookup when no lexical target exists yet instead of comparing an entire sentence with Anki `Word`.
- Grammar keeps its separate exact `Sentence` duplicate strategy.
- Editing a Batch row clears persisted duplicate-target metadata so the edited target is checked again.

## v12.0.8 - Full-text vocabulary candidate extraction

- Fixed a regression where Vocabulary extraction could stop after explicit `Vocabulary` / `Key Terms` / `Expressions` sections and return only those list items.
- Explicit lesson vocabulary remains guaranteed and is now treated as the minimum rather than the whole result.
- After explicit lists, the AI prompt now scans the entire remaining lesson for high-value words, phrases, phrasal verbs, idioms, collocations, specialist terms and reusable C1/C2 expressions.
- Content-bearing warm-up prompts, facts, discussion questions, examples, explanations and homework can contribute vocabulary; only exercise mechanics and non-content noise are skipped.
- Removed the old instructions to keep reading-text mining minimal or artificially prefer a tiny result set.
- Increased text sent to AI for Vocabulary-family import modes from 24,000 to 60,000 characters; other import modes keep the existing 24,000-character MVP limit.
- Confirmed TXT/HTML stays a local text-extraction path: HTML tags/scripts/styles are removed locally, then the cleaned text is passed to the separate AI candidate-extraction step without OCR.

## v12.0.7 - Expanded Spanish ElevenLabs voice presets

- Added user-selected Spanish ElevenLabs presets for Andalusian voices 2-5.
- Added five Peninsular Spanish presets, including the two supplied female voices.
- Added the supplied Canarian Spanish 2 preset.
- Kept the existing Spanish, Latin American and legacy Canarian presets available.
- Voice IDs are stored exactly as supplied and remain subject to ElevenLabs account/library availability; use Preview voice to verify access.

## v12.0.6 - Conversation export and in-app audio

- Added Conversation Practice export to Markdown or plain text with session metadata, transcript, session flashcards and accumulated new-card candidates.
- Added in-app audio playback for Conversation Practice so TTS no longer opens an external media player window.
- Added manual `Read tutor reply`, `Read question` and `Stop audio` controls.
- Added optional automatic reading of the tutor reply and next question; both are enabled by default when TTS is configured.
- Generate the complete cached TTS file before playback and keep the decoded audio buffer alive until playback finishes to reduce cut-off audio.
- Stop conversation audio automatically before microphone recording starts so TTS is not captured by STT.
- Play the last STT recording in-app while keeping the recording-folder diagnostic action separate.

## v12.0.5 - Conversation feedback and STT quality

- Fixed clipped Conversation Batch buttons by stacking full-width actions.
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
- Uses the current in-memory Batch cards without AnkiConnect.
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
- Added Refresh decks and Current Batch as an optional secondary source.
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

Cleaned Import Material and Conversation suggested-expression flows so reviewed candidates go through Batch instead of direct Anki writes.

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
