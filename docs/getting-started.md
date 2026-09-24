# Getting Started

## Requirements

For the current desktop development workflow you need:

- Python 3.13 (the repository `Pipfile` currently targets 3.13),
- Anki Desktop,
- the AnkiConnect add-on,
- at least one usable AI provider: a configured cloud provider or local Ollama,
- optional microphone/TTS dependencies if you want speech features.

## Install the application

```powershell
git clone https://github.com/paulinap92/ai-anki-language-assistant.git
cd ai-anki-language-assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

The default `requirements.txt` loads the hybrid/BYOK profile. The repository also contains local-only and cloud-oriented requirement files.

## Create `.env`

Start from the example file:

```powershell
Copy-Item .env.example .env
```

Then add only the provider keys and models you actually want to use. Never commit your real `.env` file.

See [Environment configuration](configuration/env.md) for details.

## Configure AnkiConnect

1. Install Anki Desktop and AnkiConnect.
2. Start Anki before exporting cards.
3. Keep the default endpoint unless you have a reason to change it:

```env
ANKI_CONNECT_URL=http://localhost:8765
```

4. Optionally set the default deck:

```env
ANKI_DECK_NAME=AI Vocabulary
```

## First launch

The main modern desktop interface is:

```powershell
python main_gui_custom.py
```

On first run, create the **Learning Profile**. It defines the learning language, target level, and explanation/feedback language used throughout the application.

## Create the first card

1. Open **Create Card**.
2. Enter a word or phrase.
3. Select **Vocabulary** or **Grammar**.
4. Generate the draft.
5. Read the generated content and any quality warnings.
6. Edit if needed.
7. Approve and send it to Anki.

!!! important
    The review step is intentional. The project does not treat model output as automatically correct learning material.

## Run the manual locally

```powershell
pip install -r requirements-docs.txt
mkdocs serve
```

This starts only a local documentation server. It does **not** deploy GitHub Pages.
