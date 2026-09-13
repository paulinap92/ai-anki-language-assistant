# AI Anki Language Assistant

Desktop application for creating reviewed language-learning Anki cards from vocabulary, grammar material, conversations, OCR/imported text and audio workflows.

The app is built around a human-in-the-loop process: AI drafts the learning content, the user reviews and edits it, and only then the card is sent to Anki.

## What it does

- Generates vocabulary and grammar cards with local Ollama or BYOK cloud providers such as Gemini, OpenAI or Claude.
- Uses the same card-generation model to self-check whether an example contains the exact target or a valid inflected/conjugated/declined form, while local code verifies the declared surface form deterministically.
- Imports TXT/HTML locally and images/PDFs through explicit OCR/import workflows.
- Extracts candidate vocabulary, grammar structures and example sentences from learning material; Vocabulary modes preserve explicit lists and continue mining useful vocabulary across the full lesson text.
- Supports Queue review before adding cards to Anki.
- Exports reviewed cards to Anki through AnkiConnect.
- Supports example audio / TTS and existing-card audio backfill, including hidden Anki metadata for TTS provider/model/voice/source tracking.
- Supports a small local Whisper STT trial for Conversation Practice.
- Tracks optional LangSmith / LLMOps quality metadata for generation, validation, review, audio and Anki outcomes.
- Keeps Import Material actions explicit: loading a screenshot/image/PDF stages it only; OCR/import runs only after the user clicks the chosen action. Vision OCR returns text only; candidate extraction is a separate review step.

## Main workflow

```text
Import / OCR / manual input
        ↓
Candidate drafts / cherry-pick
        ↓
Queue review
        ↓
AI generation
        ↓
Validation and quality warnings
        ↓
User review / edit / approve
        ↓
Anki export
        ↓
Optional audio generation or repair
```

## Interfaces

```powershell
python main_gui_custom.py
```

Starts the modern CustomTkinter GUI. This is the main interface for normal use and testing.

```powershell
python main_gui.py
```

Starts the older stable Tkinter GUI.

```powershell
python main.py
```

Starts the command-line interface.

## Core areas

| Area | Purpose |
|---|---|
| Profile | Required learner settings: learning language, target level and explanation/feedback language. This profile drives language-aware behavior across the app. |
| Setup | Choose Fully local, Hybrid / BYOK or API / BYOK, import/create `.env`, reload providers and check local Ollama. |
| Create Card | Generate and review one Vocabulary or Grammar card in one workspace. |
| Queue | Fast path for clean structured TXT/CSV/pasted rows. Choose Vocabulary, Grammar, Mixed or Provided examples before loading. |
| Import Material | Advanced/raw-source path for lessons, TXT/HTML, PDFs, screenshots, scans and mixed material. TXT/HTML are read locally; OCR/vision is only for sources that need it. |
| Speech / Audio | Test voices in Voice Lab, browse/download Piper voices, browse OpenAI and Gemini built-in voices, browse/add ElevenLabs voices with your own API key, and generate/repair Anki audio without opening an external player. |
| Fix Cards | Find and repair existing Anki cards. |
| Conversation Practice | Practise by free topic, a selected Anki deck, or current Queue. Flashcard mode adds persistent deck rotation, due/random/repeat selection, session coverage, speaking cues, genuinely new card candidates, TXT/Markdown export, and in-app tutor/question TTS. |
| Practice & Print | Practise selected cards and create printable tests. |
| Advanced / LLMOps | Optional tracing, model/cost diagnostics and local quality-event log. |


### Queue vs Import Material

Use **Queue** when the input is already clean and structured, for example one vocabulary target per line or `target | sentence` rows. Choose the input type before loading so CSV/TXT parsing is deterministic.

Use **Import Material** when the source still needs interpretation or extraction: lessons, HTML pages, PDFs, screenshots, textbook images, scans or mixed material. TXT/HTML are converted to plain text locally and do not need OCR; candidate extraction is a separate explicit step.

Import Material exposes four user-facing extraction choices:

- **Vocabulary & expressions** — scans the whole source for useful words, phrases, idioms, phrasal verbs and collocations; useful source sentences are preserved when available.
- **Grammar** — target-first cards: one concise grammar target, a compact pattern, one real usage example, learner-language explanation, contrasts and common mistakes. Smart grammar routing still handles rules, structures, transformations, exercises and sentence examples.
- **Examples / sentences** — preserves useful target + exact source-sentence pairs.
- **Auto** — lets AI classify useful items across vocabulary, grammar and source examples.

The older implementation-specific strategy names remain internal for backward compatibility and are no longer shown in the main UI.



### Global Learning Profile

Language is no longer selected independently in each workflow. The required Learning Profile is the single source of truth for target language, Conversation level, explanation/feedback language, STT language and TTS/Voice Library filtering. Piper voices are filtered to the active profile language and never silently fall back to a different-language local model.

Queue recovery also has a user-facing **Resume latest** path that summarizes the most recent autosave before loading it; manual JSON recovery remains available via **Load file…**.

## Local, Hybrid and BYOK profiles

The same application supports three user-facing setup profiles:

- **Fully local** — Ollama for AI, local faster-whisper for STT and Piper for TTS. Cloud AI providers are ignored even if old keys are present.
- **Hybrid / BYOK** — mix local components with the user's own OpenAI, Gemini, Claude, ElevenLabs or OCR API keys.
- **API / BYOK** — use the user's own cloud AI/TTS providers; local Whisper remains available for speech input in this release.

The app can start with **no AI provider configured**, but the main interface is gated behind a required local **Learning Profile**. After the profile is created, users without an AI provider are sent to **Setup** instead of seeing a startup crash. The Setup tab can create a starter `.env`, import supported values from an existing `.env`, reopen the local file, reload providers without restarting the app and check whether Ollama plus the selected local model are reachable.

Secrets stay in the local `.env`. The learner profile is stored separately in local `user_profile.json`. Clean ZIP releases do not include `.env`, `user_profile.json`, API keys, logs, caches, generated audio or runtime state.

## Quality and safety workflow

The app is designed to avoid blindly adding AI output to Anki.

It tracks or checks:

- exact input preservation;
- phrase-level meaning;
- explanation language consistency;
- grammar source focus;
- target/source sentence separation;
- quality warnings and red flags;
- duplicate detection before Anki export;
- audio sentence alignment;
- review outcomes such as added, updated, skipped or failed.

Hard warnings are used for clear structural problems such as changed input, missing required fields, wrong-script text or examples that do not use the target item. Softer warnings can be reviewed and approved manually.

## Providers

The app can use different providers for different jobs.

| Provider type | Examples | Used for |
|---|---|---|
| Card AI provider | Ollama local, Gemini, OpenAI, Claude | Vocabulary, grammar, conversation, candidate extraction. |
| OCR provider | Local Tesseract, Mistral OCR, OpenAI/Gemini Vision OCR | Image/PDF/text extraction only. Vision OCR does not create candidates directly. |
| Audio provider | ElevenLabs, OpenAI TTS, Gemini TTS, Piper local | Example audio and audio repair. |
| STT provider | Local Whisper / faster-whisper | Conversation speech-to-text trial. |

Only providers configured in `.env` are available in the UI.

## Requirements

- Python 3.10+
- Anki Desktop
- AnkiConnect add-on
- For Fully local AI: Ollama plus a pulled local model
- For BYOK cloud AI: at least one user-owned provider key

Local image/scanned-PDF OCR uses Tesseract when OCR is required, so the Tesseract executable must be installed separately for that feature.

## Setup from source

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Choose an install:

```powershell
# Fully local — no OpenAI/Gemini/Claude/Mistral/LangSmith SDKs required
pip install -r requirements-local.txt

# Hybrid / BYOK or API / BYOK
pip install -r requirements-hybrid.txt
```

`requirements.txt` remains an alias for the full Hybrid/BYOK install.

You can simply start the app with no `.env` and configure it from **Setup**, or create `.env` manually from the example:

```powershell
Copy-Item .env.example .env
```

Then start the app:

```powershell
python main_gui_custom.py
```

For local mode, set `AI_SETUP_MODE=local`, configure `OLLAMA_MODEL` and start Ollama. For BYOK mode, paste only your own keys into `.env`.

Keep Anki Desktop open while using Anki export or existing-card workflows.

## Useful `.env` groups

### Card generation

```env
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash

OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1-mini

ANTHROPIC_API_KEY=...
CLAUDE_MODEL=...
```

### Anki

```env
ANKI_CONNECT_URL=http://localhost:8765
ANKI_DECK_NAME=AI Vocabulary
DEFAULT_TARGET_LANGUAGE=English
```

### OCR

```env
MISTRAL_API_KEY=...
MISTRAL_OCR_MODEL=...
```

### Speech-to-text

Local option:

```env
STT_PROVIDER=local_whisper
WHISPER_MODEL=small
WHISPER_LANGUAGE=
```

Cloud option:

```env
STT_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_STT_MODEL=gpt-4o-mini-transcribe
WHISPER_LANGUAGE=
```

Conversation Practice passes the selected conversation language plus a short dynamic topic/flashcard context to the active STT provider. The provider can also be changed directly in **Setup → Speech-to-text**.

### Conversation audio and export

Conversation Practice can export the current session as `.md` or `.txt`. Exports include session metadata, the visible tutor/learner transcript, active flashcards and accumulated new-card candidates. Generated exports are stored outside version control by default.

Conversation TTS uses the provider/model/voice configured in **Speech / Audio**. `Read tutor reply`, `Read question`, and `Stop audio` play directly inside the application through `sounddevice`/`soundfile`; no external media-player window is required. When TTS is configured, `Auto-read tutor` and `Auto-read question` start enabled and can be switched off independently. The app generates the complete TTS file before starting playback and stops playback before microphone recording.

### Optional LangSmith / LLMOps

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=ai-anki-language-assistant
LANGSMITH_REDACT_INPUTS=true
LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com
```

LangSmith is optional. The app still runs when tracing is disabled, no API key is configured, or the `langsmith` package is missing.

## Testing

Basic syntax check:

```powershell
python -m compileall -q src
```

Targeted tests used during development include:

```powershell
python -m pytest -q tests/ai tests/anki tests/speech
```

Some tests may require optional provider SDKs or GUI dependencies.

## Documentation map

Detailed documentation is kept outside the main README:

| File | Topic |
|---|---|
| `docs/ARCHITECTURE.md` | Project structure and responsibility split. |
| `docs/OCR_IMPORT.md` | OCR/import workflows. |
| `docs/SPEECH_AND_TTS.md` | Audio/TTS workflows. |
| `docs/LLMOPS_LANGSMITH.md` | LangSmith / LLMOps setup. |
| `docs/FUTURE_PLANS.md` | Deferred features and roadmap. |
| `docs/LOCAL_FREE_MODE.md` | Ollama/Piper/local mode notes. |
| `releases/` | Detailed historical release notes. |

## Version history

The main README intentionally does not contain long version notes.

Use:

- `CHANGELOG.md` for a compact project history;
- `releases/` for detailed release notes.
