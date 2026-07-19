# AI Anki Language Assistant

Desktop application for generating vocabulary and grammar cards, practising conversations, and exporting reviewed content to Anki.

## Current interfaces

- `python main_gui.py` — classic stable Tkinter GUI.
- `python main_gui_custom.py` — modern CustomTkinter GUI with Vocabulary, Grammar, Conversation Practice, Batch / Queue, Speech / Audio, Fix Cards, Practice, and Print Test.

## Purpose

The goal of this app is to make vocabulary learning more practical.

Instead of creating simple word-translation cards manually, the app uses an LLM to generate complete flashcards with:

- translation;
- definition;
- example sentence;
- example translation;
- synonyms;
- collocations;
- grammar note;
- part of speech.

The application also supports conversation practice. Learner responses receive structured feedback, and selected expressions can be converted into Anki cards.

## Main idea

The app connects three things:

```text
User language practice
        ↓
LLM-generated correction and vocabulary explanation
        ↓
Anki flashcards saved through AnkiConnect
```

The app does not train its own AI model.
It uses configured external LLM providers such as Gemini, OpenAI, or Claude.

## Main workflows

The application has eight main workflows.

---

## Workflow 1: Create a single flashcard

This workflow is intended for a known word or phrase that should be added to Anki.

### Flow

```text
Enter a word or phrase
        ↓
Select language, explanation language, deck, and AI provider
        ↓
Generate vocabulary card with AI
        ↓
Review the generated content
        ↓
Save the card directly to Anki
```

### Example

Input:

```text
desarrollar mis habilidades
```

Generated card:

```text
Word:
desarrollar mis habilidades

Language:
Spanish

Part of speech:
phrase

Translation:
rozwijać moje umiejętności

Definition:
To improve or build your abilities in a specific area.

Example:
Quiero desarrollar mis habilidades en machine learning.

Example translation:
Chcę rozwijać moje umiejętności w machine learningu.

Synonyms:
- mejorar mis competencias
- ampliar mis conocimientos

Collocations:
- desarrollar habilidades técnicas
- desarrollar nuevas competencias
- desarrollar experiencia profesional

Grammar note:
The verb "desarrollar" is commonly used with skills, projects, ideas, and professional experience.
```

---

## Workflow 2: Practise conversation and create flashcards from it

This workflow supports written practice in a foreign language.

### Flow

```text
Select language, level, topic, deck, and AI provider
        ↓
AI asks a question
        ↓
Learner writes an answer
        ↓
AI gives feedback and correction
        ↓
AI proposes a stronger model answer
        ↓
AI suggests useful expressions
        ↓
Learner selects expressions to retain
        ↓
The app generates full Anki flashcards
        ↓
Cards are saved directly to Anki
```

### Example conversation practice

Settings:

```text
Language: Spanish
Level: Natural B1/B2
Topic: job interview
Deck: Spanish Interview Vocabulary
```

AI question:

```text
¿Por qué quieres cambiar de trabajo?
```

User answer:

```text
Quiero cambiar trabajo porque necesito más posibilidades aprender machine learning.
```

AI feedback:

```text
Your answer is understandable, but it needs a more natural structure.
```

Corrected answer:

```text
Quiero cambiar de trabajo porque necesito más oportunidades para aprender machine learning.
```

Stronger model answer:

```text
Quiero cambiar de trabajo porque busco una posición donde pueda desarrollar mis habilidades en machine learning y trabajar en proyectos más técnicos.
```

Suggested expressions:

```text
- cambiar de trabajo
- oportunidades para aprender
- desarrollar mis habilidades
- proyectos más técnicos
```

One or more suggested expressions can then be selected and converted into complete Anki cards.

---

## Workflow 3: Analyse grammar through a sentence

The modern GUI includes sentence-first grammar analysis.

Instead of selecting an abstract grammar topic, the user enters a natural sentence, for example:

```text
He might have gone out.
```

The app explains:

- the meaning of the sentence;
- the grammar structure;
- how the structure works;
- when it is used;
- a natural context;
- a contrast with a similar structure;
- a common mistake.

Grammar explanations remain in the target language and can be saved as a separate Anki grammar note type.

---

## Workflow 4: Import and review a vocabulary list

The modern GUI includes a separate **Batch / Queue** mode for working with larger vocabulary lists.

The manual single-word workflow remains available.

### Supported input

The workflow supports:

- load a `.txt` file;
- load a `.csv` file;
- paste a multiline list of words or phrases.

### Flow

```text
Load or paste a vocabulary list
        ↓
Select target language, explanation language, deck, and AI provider once
        ↓
Generate one card at a time
        ↓
Review the generated content
        ↓
Add, skip, regenerate, edit, or return to a previous item
        ↓
Move automatically to the next word
```

The queue tracks the status of each item:

```text
pending
ready
added
skipped
invalid
```

The interface also shows:

```text
current item / total
added
skipped
invalid
remaining
```

This makes it faster to process long vocabulary lists while still reviewing every card before saving it to Anki.

The Batch workflow also supports an optional **Batch topic / context** field. When it is set, the topic is sent to the LLM as a hard context constraint and saved in Batch autosave. New Anki cards created from that Batch receive a topic tag such as `topic_character_personality_traits`.

---

## Workflow 5: Backfill missing audio

The modern GUI centralises missing-audio work in **Speech / Audio**. This tab scans the selected Anki deck broadly instead of only checking the app's custom note type, so older cards, Basic notes, and already-reviewed cards can be detected when they expose recognisable fields.

Supported audio status values include:

```text
has_audio
missing_audio
missing_audio_field
malformed_audio
```

`Find missing audio` lists missing or malformed audio from all supported note types in the selected deck. An optional Anki query can narrow the scan, for example:

```text
tag:topic_character
note:Basic
is:due
```

Cards that already contain `[sound:...]` are skipped. Notes without a supported audio field are visible as `missing_audio_field`, but they are not selected for generation by default because the app should not silently change old note types. Audio batch progress is autosaved, and Pause / Stop can be used without losing completed items.

---

## Workflow 6: Fix / improve existing Anki cards

The modern GUI includes a **Fix Cards** tab for quality maintenance on cards that are already in Anki. This is separate from audio backfill: it is for flagged/leech/tagged cards, manual corrections, topic tags, and future targeted regeneration.

The tab can:

- find existing cards in the selected deck with an extra Anki query;
- filter by tag, for example `needs_fix` or `topic_character`;
- load flagged cards, for example red/orange/green/blue flags;
- load leech cards through `tag:leech`;
- find existing cards from a pasted word list;
- apply dry topic tags to selected notes, for example `topic_character_personality_traits`;
- open one selected note for manual correction;
- save corrections back to the same Anki note, preserving review history.

Topic tagging is intentionally implemented with Anki tags first. This avoids changing old note types and does not reset learning progress.

---

## Workflow 7: Practise vocabulary and grammar

The modern GUI includes a **Practice** mode that loads supported cards from Anki.

The user can:

- choose an Anki deck;
- filter the available cards;
- select the exact words or grammar structures to practise;
- practise vocabulary and grammar in a controlled session;
- check an answer without opening a modal popup;
- move to the next question;
- finish the session and review the result.

Vocabulary exercises can use:

- a sentence with a missing word or phrase;
- a definition-based question when a safe gap cannot be created;
- multiple-choice answers selected from compatible cards.

Grammar exercises ask the learner to identify the structure used in a sentence.

The user controls the material. The application randomises only the question order inside the selected set.

---

## Workflow 8: Create a printable test

The **Print Test** mode uses selected Anki cards to generate two separate HTML files:

```text
deck_name_test.html
deck_name_answer_key.html
```

The first file contains exercises without answers.

The second file contains the answer key.

Both files can be opened in a browser, printed directly, or saved as PDF.

This mode is useful for:

- offline revision;
- classroom-style exercises;
- handwritten practice;
- testing a selected vocabulary set.

---

## Non-blocking status messages

Successful actions no longer require closing a modal `OK` dialog after every card.

Instead, the application shows a status message directly in the interface, for example:

```text
Added to Anki: thorough
```

The message remains visible until the next relevant action.

The interface also keeps a short activity history.

Blocking popups are reserved for:

- real errors;
- critical warnings;
- confirmations that require a user decision.

---

## Vocabulary quality workflow

Vocabulary generation uses a **word-first** prompt.

The application:

- validates the user input;
- preserves the exact expression;
- selects context from the natural meaning and common collocations;
- rejects forced or pragmatically unnatural examples;
- checks translations;
- supports a configurable explanation language;
- supports `No translation`;
- treats multi-word expressions, compounds, idioms, and fixed phrases as complete lexical units;
- prefers the established meaning of a phrase over a literal word-by-word interpretation.

Both GUIs include an explanation-language selector.

Invalid or misspelled expressions are shown as validation warnings instead of being silently turned into fictional flashcards.


### Phrase-level meaning

For multi-word expressions, the application asks the model to analyse the complete expression before generating a definition.

For example:

```text
curso de reciclaje
```

should be interpreted in its established educational or professional meaning:

```text
refresher course / professional updating course
```

rather than automatically as:

```text
a course about recycling waste
```

This change prevents literal composition errors where a phrase is incorrectly interpreted from its individual words.


---

## Conversation level

Both GUIs allow the learner to select:

- Natural B1/B2
- Strong B2/C1
- Professional / Interview

The selected level is sent to the conversation-feedback prompt.

---

## Updating an existing Anki card

If a generated word or phrase already exists in Anki, the application does not silently create a duplicate.

Instead, it can ask whether the reviewed version should replace the existing card content.

### Flow

```text
Duplicate detected
        ↓
Display confirmation
        ↓
Update the existing note fields
        ↓
Keep the same note and review history
```

The update uses the existing Anki note instead of deleting it and creating a new one.

This is useful when a problem is discovered after a card has already been saved, for example:

- incorrect definition;
- wrong translation;
- unnatural example;
- weak collocations;
- literal interpretation of a fixed phrase.

The card content is updated while the existing Anki review history is preserved.

---

## Example Anki card view

The app creates vocabulary cards using a custom Anki note type:

```text
AI Vocabulary Light Card
```

The card is designed to be readable and useful for review.

Example front side:

```text
desarrollar mis habilidades
```

Example back side:

```text
Translation:
rozwijać moje umiejętności

Definition:
To improve or build your abilities in a specific area.

Example:
Quiero desarrollar mis habilidades en machine learning.

Example translation:
Chcę rozwijać moje umiejętności w machine learningu.

Collocations:
- desarrollar habilidades técnicas
- desarrollar nuevas competencias
- desarrollar experiencia profesional

Grammar note:
The verb "desarrollar" is commonly used with skills, projects, ideas, and professional experience.
```

---

## How the app uses LLMs

The app uses Gemini, OpenAI, or Claude to generate structured language-learning content.

The LLM is used for:

- generating vocabulary explanations;
- validating words and phrases;
- correcting learner answers;
- creating stronger model answers;
- suggesting useful expressions from conversation;
- analysing grammar through natural sentences;
- interpreting complete multi-word expressions;
- preparing structured Anki card fields;
- generating examples, collocations, and grammar notes.

The app sends the user input to the selected AI provider and expects a structured response that can be converted into Anki card data.

A provider is available only when its API key is configured in the `.env` file.

---

## Who is this app for?

This app is useful for:

- language learners who use Anki;
- people preparing for interviews in a foreign language;
- people who want to practise writing;
- learners who want vocabulary from real conversation practice;
- users who want AI-generated examples and grammar explanations;
- people who do not want to create Anki cards manually.

---

## Supported languages

The app currently supports:

- English
- Spanish
- German
- French
- Italian
- Portuguese

---

## Main features

- Generate complete AI vocabulary cards.
- Validate misspelled or invalid expressions.
- Preserve the exact user input.
- Configurable explanation language, including `No translation`.
- Save cards directly to a selected Anki deck.
- Automatically create or update a custom Anki note type.
- Practise conversation in a target language.
- Configurable conversation topic and language level.
- Structured feedback on learner answers.
- Corrected learner-answer version.
- See a stronger model answer.
- Select suggested expressions from the conversation.
- Custom expressions can be added to the flashcard queue.
- Generate multiple cards from selected expressions.
- Import vocabulary lists from TXT, CSV, or pasted multiline text.
- Review cards in a one-at-a-time Batch / Queue workflow.
- Add, skip, regenerate, edit, and navigate between queued items.
- Use an optional Batch topic / context to keep generated examples inside a selected context.
- Save topic tags such as `topic_character_personality_traits` to new cards.
- Find existing Anki cards independent of Batch autosave.
- Apply dry topic tags to existing cards without resetting Anki review history.
- Find existing cards with missing or malformed audio.
- Backfill missing audio only, without regenerating audio that already exists.
- Manually fix selected existing cards and save changes to the same Anki note with a local backup.
- Practise selected vocabulary and grammar cards from Anki.
- Generate sentence-gap and definition-based exercises.
- Create a printable test and a separate answer key.
- Use non-blocking status messages instead of success popups.
- Treat multi-word expressions as complete lexical units.
- Update an existing Anki note when a corrected version should replace a duplicate.
- Analyse grammar through natural sentences.
- Save grammar analysis as a separate Anki note type.
- Use Gemini, OpenAI, Claude, or any configured combination of these providers.

---

## Requirements

Running the application from source requires:

- Python 3.10+
- Anki Desktop
- AnkiConnect add-on installed in Anki
- At least one API key:
  - Gemini API key;
  - OpenAI API key; or
  - Anthropic API key for Claude

Running the exported `.exe` version requires:

- Windows
- Anki Desktop
- AnkiConnect add-on installed in Anki
- `.env` file placed next to the `.exe`

---


---

## Environment variables

Configuration is loaded from a local `.env` file based on `.env.example`.

Example:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1-mini

ANTHROPIC_API_KEY=your_anthropic_api_key_here
CLAUDE_MODEL=claude-haiku-4-5

ANKI_CONNECT_URL=http://localhost:8765
ANKI_DECK_NAME=AI Vocabulary
DEFAULT_TARGET_LANGUAGE=English
```

At least one configured provider key is required.

Only providers with configured API keys are displayed in the application.

For example:

- if only Gemini is configured, only Gemini is available;
- if only OpenAI is configured, only OpenAI is available;
- if only Claude is configured, only Claude is available;
- if multiple keys are configured, the user can choose between the available providers.

---

## Claude provider

Claude is available as an optional third AI provider.

It follows the same application contract as Gemini and OpenAI and supports:

- vocabulary generation;
- grammar analysis;
- conversation start;
- conversation feedback;
- Batch / Queue generation.

Claude appears in the provider selector only when `ANTHROPIC_API_KEY` is configured.

The default model can be changed through:

```env
CLAUDE_MODEL=claude-haiku-4-5
```

Claude API usage is billed separately by Anthropic. A Claude web subscription does not automatically include API usage.

---

## Anki setup

Before using the app, configure Anki.

### 1. Install Anki Desktop

Download and install Anki Desktop from the official Anki website.

### 2. Install AnkiConnect

Install the AnkiConnect add-on in Anki.

### 3. Restart Anki

Restart Anki after installing AnkiConnect.

### 4. Keep Anki running

Anki must remain running while the application is in use.

The app communicates with Anki through AnkiConnect at:

```text
http://localhost:8765
```

---

## Running the app from source code

### 1. Create a virtual environment

```bash
python -m venv .venv
```

### 2. Activate the virtual environment

PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

CMD:

```bat
.venv\Scripts\activate.bat
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

The project includes the official Anthropic Python SDK for Claude support:

```text
anthropic
```

### 4. Create `.env`

Windows CMD:

```bat
copy .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and add the required API key.

### 5. Start the classic GUI

```bash
python main_gui.py
```

### 6. Start the modern GUI

```bash
python main_gui_custom.py
```

---

## GUI entry points

This project keeps two separate GUI launchers.

### Classic stable GUI

```bash
python main_gui.py
```

This starts the original stable Tkinter GUI.

It includes:

- single flashcard creation;
- conversation practice;
- explanation-language selection;
- Anki deck selection;
- AI provider selection.

### Modern CustomTkinter GUI

```bash
python main_gui_custom.py
```

This starts the modern CustomTkinter GUI.

It includes:

- vocabulary generation;
- grammar analysis;
- conversation practice;
- Batch / Queue vocabulary import;
- Practice mode;
- Print Test generation;
- explanation-language selection;
- selectable conversation level;
- non-blocking status messages;
- updating existing Anki cards.

### Command-line mode

```bash
python main.py
```

Available CLI commands while the app is running:

```text
/model      change AI provider
/language   change target language
/deck       change Anki deck
stop        close the app
exit        close the app
quit        close the app
q           close the app
```

---


---


---

## Clean project structure

```text
ai_anki_vocab_multi_cards/
├── main.py                         # CLI entry point
├── main_gui.py                     # Stable Tkinter GUI entry point
├── main_gui_custom.py              # Modern CustomTkinter GUI entry point
├── requirements.txt
├── .env.example
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ANKI_CARD_MODEL.md
│   ├── DEVELOPMENT_NOTES.md
│   ├── PROMPT_ENGINEERING_HISTORY.md
│   └── VIDEO_SCRIPT_PROMPT_ENGINEERING.md
└── src/
    ├── ai/
    │   ├── base.py                 # Abstract AI provider interface and JSON parsing
    │   ├── factory.py              # Builds configured providers
    │   ├── prompts.py              # Prompt builders and validation instructions
    │   └── providers/
    │       ├── gemini.py           # Gemini provider
    │       ├── openai_provider.py  # OpenAI provider
    │       └── claude.py           # Claude provider
    ├── anki/
    │   ├── client.py               # AnkiConnect API wrapper
    │   ├── field_builder.py        # Converts cards to safe Anki fields
    │   └── templates.py            # HTML/CSS Anki card templates
    ├── cli/
    │   └── app.py                  # Command-line workflow
    ├── core/
    │   └── config.py               # Environment-backed settings
    ├── domain/
    │   ├── languages.py            # Supported languages and aliases
    │   └── models.py               # Pydantic data models
    └── ui/
        ├── classic_gui.py          # Stable Tkinter GUI
        └── modern_gui.py           # CustomTkinter GUI
```

---

## Anki note models

Vocabulary cards use:

```text
AI Vocabulary Light Card
```

Grammar cards use:

```text
AI Grammar Light Card
```

The app creates and updates these note types automatically.

---

## Old card migration

Older cards created as `Basic` notes can be migrated safely.

Recommended flow:

1. Start the stable GUI.
2. Select **Prepare style for old AI cards**.
3. Select the displayed cards in Anki Browse.
4. Open **Notes → Change Note Type**.
5. Select `AI Vocabulary Light Card · Migrated`.
6. Map `Front → Front` and `Back → Back`.

This preserves review history because the final note-type conversion happens inside Anki.

---

## Speech and example audio

The modern GUI supports optional example-sentence audio through a dedicated speech layer. Available TTS providers depend on local configuration and can include ElevenLabs, OpenAI TTS, Gemini TTS, and Piper offline.

Audio can be generated while reviewing a new vocabulary card or added later to selected existing cards with an empty `Audio` field. Generated media is stored in Anki and referenced with `[sound:filename]`, preserving existing note and review history.

Audio generation is on demand and uses a deterministic local cache based on sentence, language, provider, model, and voice.

See `docs/SPEECH_AND_TTS.md`.

---

## Development

Install with Pipenv and run tests with coverage:

```bash
pipenv install --dev
pipenv run python -m pytest --cov=src --cov-report=term-missing --cov-report=html
```

Run a syntax check after changes:

```bash
python -m compileall src main.py main_gui.py main_gui_custom.py
```

The application is split by responsibility:

```text
domain models        do not know about UI or APIs
AI providers         do not know about Anki
Anki client          does not know about prompts
UI                   coordinates user actions and calls services
```

This keeps the project easier to test, maintain, and extend.

See:

- `docs/PROMPT_ENGINEERING_HISTORY.md`
- `docs/VIDEO_SCRIPT_PROMPT_ENGINEERING.md`
- `docs/BATCH_QUEUE_MODE.md`
- `docs/PRACTICE_AND_PRINT_MODE.md`
- `docs/ANKI_UPDATE_EXISTING_CARDS.md`
- `docs/CLAUDE_PROVIDER.md`
- `docs/UX_FEEDBACK_HISTORY.md`
- `docs/ARCHITECTURE.md`

---

## Troubleshooting

### Anki cards are not saved

Check that:

- Anki Desktop is open;
- AnkiConnect is installed;
- AnkiConnect is enabled;
- `ANKI_CONNECT_URL` is correct in `.env`;
- the selected Anki deck exists or can be created.

### AI provider is not available

Check that:

- `.env` exists;
- the correct provider key is configured;
- the model name is correct;
- the required provider SDK is installed;
- the app was restarted after editing `.env`.

Claude requires:

```env
ANTHROPIC_API_KEY=...
CLAUDE_MODEL=...
```

### The app does not start

Check that:

- dependencies are installed;
- the virtual environment is activated;
- Python version is 3.10 or newer;
- `.env` exists if running the full AI workflow.


---

## Future improvements

Possible next improvements:

- expand automated test coverage;
- improve prompt evaluation and regression testing;
- expand Practice exercise types;
- improve Print Test configuration;
- add speech input/output;
- add more card templates;
- improve error messages;
- add import/export of user settings;
- add packaging scripts for Windows releases.


---

## Simple Auto Batch

The modern GUI includes a safer Auto Batch workflow built on top of the stable TTS version.

### Batch actions

- `Auto-generate pending` generates cards one by one.
- `Add all ready` adds only cards with status `ready`.
- Invalid, duplicate, or error cards remain in review.

### Safety behavior

- Batch sessions are autosaved to `batch_autosaves/`.
- Runtime logs are written to `logs/ai_anki_app.log`.
- `Add all ready` runs step by step through the GUI event loop, not through a worker thread.
- Existing Anki notes are fetched once before bulk add to reduce repeated duplicate scans.
- A failed card is marked as `error` and the process continues with the next card.


---

## Audio diagnostics

TTS generation and Anki audio attachment now write detailed runtime information to:

```text
logs/ai_anki_app.log
```

The log records:

- selected TTS provider, model, and voice;
- whether audio came from cache or provider;
- generated audio cache path;
- Anki media upload attempts;
- Audio field updates;
- failures when attaching audio to new or existing cards.

Changing the main card language refreshes the TTS voice preset list so language-specific voices are shown when available.


---

## Version 7.2: Auto Batch rate-limit fix

Auto Batch now treats provider rate-limit errors as a stop condition instead of
retrying the same item repeatedly.

Behavior:

- only `pending` items are auto-generated;
- `invalid`, `error`, and `rate_limited` items are not retried automatically;
- HTTP 429 / `Too Many Requests` stops Auto Batch;
- the Batch session is autosaved before stopping;
- the user can resume later after the provider limit cools down.

This prevents rapid retry loops that can repeatedly call the provider after a
rate-limit response.

---

## v8.1.2 UI logic cleanup

### Speech / Audio

`Speech / Audio` is now the only place for missing-audio backfill.

Use:

1. Select the Anki deck.
2. Optional: add an Anki filter such as `tag:topic_character`, `note:Basic`, or `is:due`.
3. Choose the source text field for TTS.
4. Choose the target audio field.
5. Choose the write mode.
6. Click `Find missing audio`.
7. Click `Select ready`.
8. Click `Generate audio for selected`.

For old Basic cards without an `Audio` field, use legacy append mode:

```text
Source text field: Front / Back / Example
Target audio field: Back
Write mode: Append [sound] to existing field
```

This appends `[sound:...]` to an existing field without changing the note type.

`Pause audio` and `Stop audio` are enabled only while an audio batch is running.

### Batch duplicate precheck

`Add all ready` now performs an explicit duplicate precheck before writing to Anki.

The app shows:

- new cards;
- safe duplicates in the current app note type;
- uncertain/legacy duplicates.

The user must choose one explicit action:

- `Add new only / skip duplicates`;
- `Update safe duplicates`;
- `Review duplicates first`;
- `Cancel`.

Legacy/Basic duplicates are not auto-updated. They are marked for review instead.

### Fix Cards

`Fix Cards` is for maintenance of existing Anki notes:

- search by optional Anki filter;
- load flagged/leech/needs_fix cards;
- find notes from a pasted word list;
- apply topic tags;
- edit one selected note and save it back to the same Anki note.

Rows show an action status such as `found`, `topic_tagged`, or `saved_to_anki`.

## v8.1.3 hotfix notes

- Auto Batch performs a broad duplicate precheck before provider API calls. Existing pending words are marked as duplicates and skipped before Gemini/OpenAI/Claude are used.
- Add All summaries now include failure reasons, not only a failed count.
- Speech / Audio refreshes progress after each item.
- Fix Cards editor is focused/modal when opened.
- UI wording uses `topic/context`, not mixed-language labels.

## v8.1.3.3 Fix Cards audio repair

`Fix Cards` now includes a targeted audio repair action for one existing Anki note.

Workflow:

1. Load cards with `Find cards`, `Load flagged`, `Load needs_fix`, or `Find words from list`.
2. Select exactly one card.
3. Click `Fix audio` / `Fix selected audio`.
4. Choose the source text field, for example `Example`, `Back`, `Word`, or `Front`.
5. Choose the target field.
6. Generate and listen to an audio preview.
7. Click `Replace audio in Anki`.

The update is written to the same Anki note, so review history is preserved. If the target field already contains `[sound:...]`, the app asks for confirmation before replacing it. A local backup is written to `existing_card_backups/` before the update, and the note receives the tag `ai_audio_fixed`.

For old Basic cards without a dedicated `Audio` field, use `Append/replace [sound] in target field` and choose a visible field such as `Back`.

## v8.1.4 prompt quality and validation

The vocabulary prompt now uses `v5-topic-quality-validation`.

Topic/context remains user-defined. You can type any Batch topic, for example:

- `character / personality traits`
- `Mundo laboral`
- `Spanish bureaucracy and appointments`
- `food culture and restaurants`

The app treats the user topic as a hard context constraint in the prompt. Known topic presets only add optional extra hints; they do not replace the user's text and they do not limit the allowed topics.

Generated cards now include provider self-check fields:

- `topic_fit`
- `topic_warning`
- `quality_warnings`

The app also runs local validation before adding cards to Anki. It checks for obvious problems such as:

- changed input phrase,
- wrong target language,
- wrong explanation language,
- Cyrillic in Polish/Spanish/English/German/Italian explanation fields,
- Polish mistakes such as `nostalgja`, `głęboka smutek`, or `область живота`,
- empty required fields,
- weak provider topic fit.

Warnings are shown in preview/autosave and require confirmation before adding to Anki. This validation is intentionally lightweight; it is not a full grammar checker.


### v8.1.4.2 — Quality validator sanity

- Polish diacritics no longer trigger false Spanish-looking warnings.
- English grammar examples such as `a`, `the`, `on`, `for` in Polish grammar notes no longer trigger noisy mixed-language warnings.
- Hard quality warnings, such as Cyrillic in Polish fields, now block Anki writes until edited.
- Exact-input validation ignores outer quote marks around phrases such as `"Nevertheless…"`.

## v8.1.4.3 notes

This hotfix focuses on sanity checks discovered during real Anki use:

- Vocabulary examples must use the target word/phrase itself or a valid inflected/conjugated form. Spanish verbs such as `derrumbar(se)`, `enfurecer(se)` and `encolerizarse` are locally checked so examples do not silently use a synonym or a visually similar wrong verb.
- Batch final summary now reports the whole queue: added, updated, duplicates, invalid/blocked, failed, rate-limited and remaining items.
- Speech / Audio now has `Test TTS provider`. Audio batch runs a small preflight first and does not start when provider diagnostics fail, for example ElevenLabs `401 Unauthorized` or missing API key.

## v8.1.5 TTS and prompt-quality cleanup

Before adding OCR, the app now has a safer TTS preflight and a stronger vocabulary quality layer.

### TTS diagnostics

Use **Speech / Audio → Test TTS provider** before long audio batches. The diagnostic checks the selected provider, key/auth status, model, voice, and a short sample generation. If diagnostics fail, audio batch will not start. This is especially important for ElevenLabs, which is optional/premium and can fail because of API key, voice/model access, billing, or quota.

### Prompt and validation

The vocabulary prompt is now `v7-natural-target-usage`. Generated examples must use the target item itself or a valid inflected/conjugated form, not a synonym or visually similar typo. The app also surfaces self-check fields for target usage, collocation naturalness, and translation naturalness.

The local validator is language-neutral: it no longer has a special Spanish-only branch. It checks lexical anchors for all languages and warns when the example does not appear to teach the requested item. It also catches known awkward cases from real tests, such as `come across rain`, `mesmerizing flow of the smoothie`, and `wear down doubts`.


## v8.1.5.2 language-neutral schema/defaults

Vocabulary generation now separates the language being learned from the language used for translations/explanations.

- **Target language** is the language of the word/phrase and example sentence.
- **Explanation language** is the language used for translation, example translation, and short usage/grammar notes.
- Batch now exposes both settings visibly instead of relying on a hidden Polish default.
- Conversation Practice now exposes **Feedback language** separately from the conversation target language.
- New generated cards use language-neutral schema fields: `translation` and `example_translation`.
- Legacy autosaves/provider responses with `translation_pl` and `example_pl` are still accepted.
- The Anki note type now includes neutral fields `Translation` and `ExampleTranslation` while keeping `TranslationPL` and `ExamplePL` for compatibility with older cards/templates.

Polish can still be selected as the preferred explanation language, but it is no longer treated as an invisible architectural assumption.
