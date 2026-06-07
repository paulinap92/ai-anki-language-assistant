# Architecture

## Goal

This project is a local language-learning assistant. It generates structured vocabulary cards with an AI provider and saves them to Anki through AnkiConnect.

The refactor keeps the existing behaviour but separates the code into clear responsibility areas.

## Main layers

### `src/domain`

Contains pure application concepts:

- `VocabularyCard`
- `ConversationStart`
- `ConversationFeedback`
- supported languages and aliases

This layer has no dependency on GUI, Anki, OpenAI, Gemini, or environment variables.

### `src/core`

Contains application configuration loaded from environment variables.

`get_settings()` reads `.env` through `python-dotenv` and returns a `Settings` dataclass.

### `src/ai`

Contains the AI abstraction and provider implementations.

- `base.py` defines `VocabularyAiClient`.
- `prompts.py` builds prompts.
- `factory.py` creates only providers that have configured API keys.
- `providers/gemini.py` implements Gemini.
- `providers/openai_provider.py` implements OpenAI.

All providers return validated Pydantic models, not raw JSON strings.

### `src/anki`

Contains all Anki-related logic.

- `client.py` communicates with AnkiConnect.
- `templates.py` stores note type names, fields, HTML templates, and CSS.
- `field_builder.py` converts validated `VocabularyCard` objects into HTML-safe Anki fields.

### `src/ui`

Contains desktop interfaces.

- `classic_gui.py` is the stable Tkinter UI.
- `modern_gui.py` is the CustomTkinter UI.

The UI does not build prompts or call AnkiConnect directly. It calls the AI clients and `AnkiClient`.

### `src/cli`

Contains the command-line workflow.

## Import policy

This version does not keep legacy compatibility wrapper modules. All runtime code imports from the explicit package structure:

- `src.domain.*` for domain models and language utilities
- `src.ai.*` for AI clients, prompts, and provider selection
- `src.anki.*` for AnkiConnect integration and card templates
- `src.ui.*` for graphical interfaces
- `src.cli.*` for the command-line interface
- `src.core.*` for configuration

Old flat imports such as `src.models`, `src.anki_client`, `src.gui`, or `src.prompts` are intentionally not supported anymore.

## Data flow

```text
User input
  ↓
GUI or CLI
  ↓
VocabularyAiClient implementation
  ↓
Prompt builder
  ↓
Gemini/OpenAI
  ↓
Pydantic model validation
  ↓
Anki field builder
  ↓
AnkiClient
  ↓
AnkiConnect
  ↓
Anki deck
```

## Design rule

When adding new features, keep the same separation:

- new provider → `src/ai/providers/`
- new card layout → `src/anki/templates.py`
- new Anki field rendering logic → `src/anki/field_builder.py`
- new UI behaviour → `src/ui/`
- new shared data model → `src/domain/models.py`
