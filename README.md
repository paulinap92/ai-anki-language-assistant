# AI Anki Language Assistant

Desktop application for generating vocabulary and grammar cards, practising conversations, and exporting reviewed content to Anki.

## Current interfaces

- `python main_gui.py` — classic stable Tkinter GUI.
- `python main_gui_custom.py` — modern CustomTkinter GUI with Vocabulary, Grammar, and Conversation Practice.

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

The app can also help with conversation practice. You answer AI-generated questions, receive feedback, and then convert useful expressions from the conversation into Anki cards.

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
It uses configured external LLM providers such as Gemini or OpenAI.

## Main workflows

The application has three main workflows.

---

## Workflow 1: Create a single flashcard

Use this workflow when you already know the word or phrase you want to learn.

### Flow

```text
Enter a word or phrase
        ↓
Choose language, explanation language, deck, and AI provider
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

Use this workflow when you want to practise writing in a foreign language.

### Flow

```text
Choose language, level, topic, deck, and AI provider
        ↓
AI asks a question
        ↓
You write your answer
        ↓
AI gives feedback and correction
        ↓
AI proposes a stronger model answer
        ↓
AI suggests useful expressions
        ↓
You select expressions you want to remember
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

You can then select one or more expressions and generate full Anki cards from them.

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

## Vocabulary quality workflow

Vocabulary generation uses a **word-first** prompt.

The application:

- validates the user input;
- preserves the exact expression;
- selects context from the natural meaning and common collocations;
- rejects forced or pragmatically unnatural examples;
- checks translations;
- supports a configurable explanation language;
- supports `No translation`.

Both GUIs include an explanation-language selector.

Invalid or misspelled expressions are shown as validation warnings instead of being silently turned into fictional flashcards.

---

## Conversation level

Both GUIs allow the learner to select:

- Natural B1/B2
- Strong B2/C1
- Professional / Interview

The selected level is sent to the conversation-feedback prompt.

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

The app uses Gemini or OpenAI to generate structured language-learning content.

The LLM is used for:

- generating vocabulary explanations;
- validating words and phrases;
- correcting learner answers;
- creating stronger model answers;
- suggesting useful expressions from conversation;
- analysing grammar through natural sentences;
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
- Choose the explanation language or use `No translation`.
- Save cards directly to a selected Anki deck.
- Automatically create or update a custom Anki note type.
- Practise conversation in a target language.
- Choose conversation topic and language level.
- Receive feedback on your answer.
- See a corrected version of your answer.
- See a stronger model answer.
- Select suggested expressions from the conversation.
- Add your own custom expressions to the flashcard queue.
- Generate multiple cards from selected expressions.
- Analyse grammar through natural sentences.
- Save grammar analysis as a separate Anki note type.
- Use Gemini, OpenAI, or both, depending on configured API keys.

---

## Requirements

To use the app from source code, you need:

- Python 3.10+
- Anki Desktop
- AnkiConnect add-on installed in Anki
- At least one API key:
  - Gemini API key, or
  - OpenAI API key

To use the exported `.exe` version, you need:

- Windows
- Anki Desktop
- AnkiConnect add-on installed in Anki
- `.env` file placed next to the `.exe`

---

## Important security note

The `.env` file contains private API keys.

Do not publish it on GitHub.
Do not send it to people you do not trust.
Do not include it in public releases.

For private family testing, the `.env` file can be placed next to the `.exe`, but this means that the app will use the same API key.

Recommended private distribution structure:

```text
AI_Anki_App/
├── main_gui.exe
├── .env
└── README_PL.txt
```

Do not delete the `.env` file, because the app needs it to connect to the AI provider.

---

## Environment variables

Create a `.env` file based on `.env.example`.

Example:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1-mini

ANKI_CONNECT_URL=http://localhost:8765
ANKI_DECK_NAME=AI Vocabulary
DEFAULT_TARGET_LANGUAGE=English
```

At least one API key is required.

If only Gemini is configured, only Gemini will be available.
If only OpenAI is configured, only OpenAI will be available.
If both are configured, both providers can be used.

---

## Anki setup

Before using the app, configure Anki.

### 1. Install Anki Desktop

Download and install Anki Desktop from the official Anki website.

### 2. Install AnkiConnect

Install the AnkiConnect add-on in Anki.

### 3. Restart Anki

After installing AnkiConnect, restart Anki.

### 4. Keep Anki open

Anki must be open while using this app.

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

### 4. Create `.env`

Windows CMD:

```bat
copy .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` and add your API key.

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
- explanation-language selection;
- selectable conversation level.

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

## Running the exported Windows version

If you received the app as an `.exe`, use this flow.

### Folder structure

Keep all files in one folder:

```text
AI_Anki_App/
├── main_gui.exe
├── .env
└── README_PL.txt
```

### How to run

1. Open Anki Desktop.
2. Make sure AnkiConnect is installed.
3. Keep Anki open.
4. Open `main_gui.exe`.
5. Choose language, explanation language, deck, and AI provider.
6. Generate flashcards or start conversation practice.
7. Save selected cards to Anki.

### Windows warning

Windows may show a warning because the `.exe` is private and not signed with a paid certificate.

If you trust the source of the file, click:

```text
More info → Run anyway
```

or in Polish Windows:

```text
Więcej informacji → Uruchom mimo to
```

---

## Building the Windows `.exe`

Install PyInstaller:

```bash
pip install pyinstaller
```

Build the stable GUI:

```bash
pyinstaller --onefile --windowed main_gui.py
```

The generated file will be available in:

```text
dist/main_gui.exe
```

If the app uses additional folders such as `assets`, `prompts`, or templates, include them with `--add-data`.

Example for Windows:

```powershell
pyinstaller --onefile --windowed main_gui.py `
  --add-data "assets;assets" `
  --add-data "prompts;prompts"
```

Do not embed `.env` inside the `.exe`.
Place `.env` next to the `.exe`.

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
    │       └── openai_provider.py  # OpenAI provider
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

1. Open the stable GUI.
2. Click **Prepare style for old AI cards**.
3. In Anki Browse, select the shown cards.
4. Choose **Notes → Change Note Type**.
5. Select `AI Vocabulary Light Card · Migrated`.
6. Map `Front → Front` and `Back → Back`.

This preserves review history because the final note-type conversion happens inside Anki.

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
- the API key is correct;
- the model name is correct;
- the app was restarted after editing `.env`.

### The app does not start

Check that:

- dependencies are installed;
- the virtual environment is activated;
- Python version is 3.10 or newer;
- `.env` exists if running the full AI workflow.

### Windows blocks the `.exe`

This can happen because the app is not signed with a paid code-signing certificate.

If you trust the app source, choose:

```text
More info → Run anyway
```

---

## Future improvements

Possible next improvements:

- expand automated test coverage;
- improve prompt evaluation and regression testing;
- add speech input/output;
- add more card templates;
- improve error messages;
- add import/export of user settings;
- add packaging scripts for Windows releases.
