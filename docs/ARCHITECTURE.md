# Architecture

## Goal

AI Anki Language Assistant is a local desktop application that generates structured language-learning content with configurable LLM providers and saves reviewed material to Anki through AnkiConnect.

The codebase separates domain models, provider integrations, Anki logic, UI workflows, and configuration.

## Main layers

### `src/domain`

Contains validated application models and language utilities.

Main models include:

- `VocabularyCard`
- `ConversationStart`
- `ConversationFeedback`
- `GrammarAnalysis`

This layer has no dependency on GUI frameworks, AnkiConnect, provider SDKs, or environment variables.

### `src/core`

Contains configuration loaded from environment variables plus user-facing setup helpers.

`get_settings()` reads `.env` and exposes provider keys, model names, Anki settings, defaults and the selected `AI_SETUP_MODE` (`local`, `hybrid`, or `api`). The GUI is allowed to start with no configured AI provider so first-run setup remains accessible.

`user_setup.py` creates/imports supported `.env` values, backs up the existing file before import, reports configured/missing components without exposing secrets and checks local Ollama availability.

### `src/ai`

Contains the provider abstraction, prompt builders, response parsing, and provider implementations.

- `base.py` defines the common AI client contract and central parsing logic.
- `prompts.py` builds vocabulary, grammar, and conversation prompts.
- `factory.py` registers only providers allowed by the selected setup profile. Cloud provider imports are lazy so the local install does not require cloud SDKs.
- `providers/ollama.py` implements local Ollama.
- `providers/gemini.py` implements Gemini.
- `providers/openai_provider.py` implements OpenAI.
- `providers/claude.py` implements Claude through the Anthropic Messages API.

All providers reuse the same prompts and validated domain models.

### `src/anki`

Contains AnkiConnect integration.

- `client.py` sends AnkiConnect actions.
- `templates.py` stores note types, fields, card templates, and CSS.
- `field_builder.py` converts validated models into escaped Anki fields.

The Anki layer also supports:

- deck discovery;
- note creation;
- duplicate detection;
- updating existing notes;
- reading cards for Practice and Print Test;
- querying new, due, and overdue cards.

### `src/ui`

Contains desktop interfaces.

- `classic_gui.py` provides the stable Tkinter GUI.
- `modern_gui.py` provides the unified Create Card (Vocabulary/Grammar), Conversation Practice, Batch, Import Material, Speech / Audio, Practice, and Print Test workflows.

The UI coordinates services but does not build prompts or manually construct AnkiConnect payloads.

### `src/cli`

Contains the command-line workflow.

## Import policy

Runtime code imports only from the explicit package structure:

- `src.domain.*`
- `src.core.*`
- `src.ai.*`
- `src.anki.*`
- `src.ui.*`
- `src.cli.*`

Legacy compatibility wrapper modules are intentionally not kept.

## Vocabulary flow

```text
User input
→ GUI or CLI
→ prompt builder
→ selected provider
→ structured JSON response
→ Pydantic validation
→ exact-input validation
→ field builder
→ duplicate check / update decision
→ AnkiConnect
```

## Grammar flow

```text
Sentence
→ analyze_grammar()
→ provider-specific text generation
→ GrammarAnalysis validation
→ Grammar field builder
→ AI Grammar Light Card
```

## Conversation flow

```text
Mode A: topic + level
→ start_conversation(..., flashcard_context="")
→ learner answer
→ review_conversation_answer(..., flashcard_context="")
→ feedback + corrected answer + topic vocabulary suggestions
→ editable suggestion basket
→ Batch

Mode B: selected Anki deck or current Batch + optional topic focus
→ select cards: Continue rotation / Anki due / Random / Repeat last session
→ build bounded flashcard context (up to 30 session cards)
→ persist rotation only after conversation start succeeds
→ start_conversation(..., flashcard_context="...")
→ track which session targets have actually appeared in the conversation
→ rebuild context with NOT USED YET targets before ALREADY USED targets
→ learner answer
→ review_conversation_answer(..., flashcard_context="...", conversation_history="...")
→ corrections + tutor reply + next question
→ expressions to use next (practice cues; may reuse existing cards)
→ 0–3 genuinely new flashcard candidates per turn, accumulated for the session
→ explicit staging and send to Batch
```

Flashcard-based Conversation reads either a selected deck through AnkiConnect or the current in-memory Batch. Context building is isolated in `src/conversation/flashcard_context.py`; persistent session selection/rotation lives in `src/conversation/selection.py`; suggestion separation and duplicate/relevance filtering live in `src/conversation/suggestions.py`. Exact deck targets are practice material and cannot become new-card candidates; longer grounded collocations remain allowed. Local rotation progress is stored in `conversation_rotation_state.json`, which is ignored by Git and is not part of clean releases.

## Batch flow

Batch is intentionally the clean-input path. The user selects the mode before loading.

```text
Choose mode (Vocabulary / Grammar / Mixed / Provided examples)
→ clean TXT / CSV / pasted rows
→ mode-aware parsing (e.g. target + sentence columns)
→ normalise and deduplicate
→ queue items
→ generate one item
→ review
→ Add / Skip / Regenerate / Edit
→ automatic advance
→ optional JSON session persistence
```

Raw lessons, HTML pages, PDFs, screenshots and scans belong in Import Material first. TXT/HTML text extraction is local and bypasses OCR; OCR/vision is reserved for PDF/image material that needs it.

## Practice flow

```text
Selected Anki deck
→ find supported notes/cards
→ user selects material
→ local exercise generation
→ local answer checking
→ inline feedback
```

Practice does not call an LLM for ordinary multiple-choice checking.

## Print Test flow

```text
Selected Anki cards
→ local exercise generation
→ test HTML
→ separate answer-key HTML
```

## Existing-card update flow

```text
exact match found
→ ask user
→ updateNoteFields
→ keep note ID and review history
```

## Provider design

Gemini, OpenAI, and Claude implement the same application contract.

Provider selection remains dynamic: configured providers are filtered by the selected setup profile. `local` activates local providers, `api` activates BYOK cloud providers, and `hybrid` exposes both.

## Design rules

- New provider → `src/ai/providers/`
- New prompt → `src/ai/prompts.py`
- New shared model → `src/domain/models.py`
- New Anki note field → domain model + template + field builder
- New reusable Anki action → `src/anki/client.py`
- New workflow UI → `src/ui/`
- Provider-specific code must not duplicate parsing or validation logic


### `src/speech`

Contains TTS abstractions, provider factories, deterministic audio caching, and speech application services. Text providers and speech providers remain independent.

Speech flow:

```text
Voice Lab sample → SpeechService → cache → InternalAudioPlayer
Example sentence → SpeechService → TTS provider → cache → Anki media → Audio field
```

Preview playback is in-app through `InternalAudioPlayer`; external OS media players are used only by explicitly named open-file/folder actions.

LangChain and LangGraph are not required for the current deterministic workflows. LangGraph remains a possible later fit for stateful Auto Batch orchestration with checkpoints and human review.


## Simple Auto Batch architecture

The Auto Batch implementation intentionally avoids worker threads. Long operations
are split into small steps scheduled through the Tk event loop:

```text
Auto-generate pending
→ generate one item
→ autosave
→ schedule next item with after()

Add all ready
→ add one ready card
→ autosave
→ update progress
→ schedule next card with after()
```

This keeps GUI updates on the main Tk thread and reduces thread-safety risk.

### Conversation STT and compact coaching (v12.0.5)

Conversation Practice supplies faster-whisper with an explicit ISO language code and a bounded dynamic initial prompt built from the topic, recent turns, active flashcard targets and speaking cues. Local STT uses VAD before transcription. Conversation feedback classifies coaching items as `error`, `improvement`, or `possible_transcription`; the GUI renders only compact coaching by default and keeps corrected/advanced answers plus mini practice behind the `Detailed coaching` switch.

### Conversation export and in-app audio (v12.0.6)

Conversation transcript export is handled by `src/conversation/export.py`, which renders UTF-8 Markdown/TXT independently of Tkinter. Conversation auto-read text selection is kept in `src/conversation/audio.py`. `src/speech/playback.py` provides in-process playback through `sounddevice` + `soundfile`; TTS generation remains in `SpeechService` and its deterministic cache. The GUI waits for a complete generated file before playback, invalidates stale audio requests when a new one starts, and stops playback before microphone recording.
