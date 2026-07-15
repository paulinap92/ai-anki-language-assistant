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

Contains configuration loaded from environment variables.

`get_settings()` reads `.env` and exposes provider keys, model names, Anki settings, and defaults.

### `src/ai`

Contains the provider abstraction, prompt builders, response parsing, and provider implementations.

- `base.py` defines the common AI client contract and central parsing logic.
- `prompts.py` builds vocabulary, grammar, and conversation prompts.
- `factory.py` registers only providers with configured API keys.
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
- `modern_gui.py` provides Vocabulary, Grammar, Conversation Practice, Batch / Queue, Practice, and Print Test workflows.

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
Topic + level
→ start_conversation()
→ learner answer
→ review_conversation_answer()
→ feedback + corrected answer + suggested vocabulary
→ optional vocabulary-card generation
→ Anki
```

## Batch / Queue flow

```text
TXT / CSV / pasted list
→ normalise and deduplicate
→ queue items
→ generate one item
→ review
→ Add / Skip / Regenerate / Edit
→ automatic advance
→ optional JSON session persistence
```

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

Provider selection remains dynamic: a provider appears only when its API key is configured.

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
Example sentence → SpeechService → TTS provider → cache → Anki media → Audio field
```

LangChain and LangGraph are not required for the current deterministic workflows. LangGraph remains a possible later fit for stateful Auto Batch orchestration with checkpoints and human review.
