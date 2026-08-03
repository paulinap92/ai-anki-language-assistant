# AI Anki Language Assistant

Desktop application for creating reviewed language-learning Anki cards from vocabulary, grammar material, conversations, OCR/imported text and audio workflows.

The app is built around a human-in-the-loop process: AI drafts the learning content, the user reviews and edits it, and only then the card is sent to Anki.

## What it does

- Generates vocabulary and grammar cards with Gemini, OpenAI or Claude.
- Imports text, images and PDFs through explicit OCR/import workflows.
- Extracts candidate vocabulary, grammar structures and example sentences from learning material.
- Supports Batch / Queue review before adding cards to Anki.
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
Batch / Queue review
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
| Single flashcard | Generate and review one vocabulary card. |
| Batch / Queue | Process lists of vocabulary, grammar and provided-example items. |
| Grammar | Analyse grammar through a sentence or structure. |
| Import Material | OCR/import text, review source material and extract candidate drafts. |
| Speech / Audio | Generate or repair example audio for Anki cards. |
| Fix Cards | Find and repair existing Anki cards. |
| Conversation Practice | Practise writing/speaking and stage useful expressions for Batch. |
| Practice & Print | Practise selected cards and create printable tests. |
| LLMOps / LangSmith | Optional tracing and local quality-event log. |

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
| Card AI provider | Gemini, OpenAI, Claude | Vocabulary, grammar, conversation, candidate extraction. |
| OCR provider | Local Tesseract, Mistral OCR, OpenAI/Gemini Vision OCR | Image/PDF/text extraction only. Vision OCR does not create candidates directly. |
| Audio provider | ElevenLabs, OpenAI TTS, Gemini TTS, Piper local | Example audio and audio repair. |
| STT provider | Local Whisper / faster-whisper | Conversation speech-to-text trial. |

Only providers configured in `.env` are available in the UI.

## Requirements

- Python 3.10+
- Anki Desktop
- AnkiConnect add-on
- At least one configured card-generation provider key: Gemini, OpenAI or Claude

Optional features require their own dependencies and API keys, for example Mistral OCR, ElevenLabs/OpenAI/Gemini TTS, Piper local or faster-whisper.

## Setup from source

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create `.env` from the example:

```powershell
Copy-Item .env.example .env
```

Add at least one card AI provider key, then start the app:

```powershell
python main_gui_custom.py
```

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

### Speech-to-text trial

```env
STT_PROVIDER=local_whisper
WHISPER_MODEL=base
WHISPER_LANGUAGE=
```

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
