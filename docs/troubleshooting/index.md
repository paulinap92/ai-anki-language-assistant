# Troubleshooting

## A provider does not appear

Check:

1. the active `AI_SETUP_MODE`,
2. whether the required API key/model value is really present,
3. whether the value is not an example/placeholder,
4. whether the provider is actually implemented in the current version.

Groq and OpenRouter AI providers are planned but are not part of the current v12.4.8 AI factory.

## Anki export fails

- Start Anki Desktop.
- Confirm AnkiConnect is installed and enabled.
- Check `ANKI_CONNECT_URL` (default: `http://localhost:8765`).
- Confirm the target deck is available.
- If the message reports a duplicate, review the existing note instead of trying to bypass the duplicate guard.

## OpenAI Cloud STT is unavailable

Check that:

```env
STT_PROVIDER=openai
OPENAI_API_KEY=...
```

are configured. Without a valid OpenAI key, the STT factory intentionally returns no OpenAI STT service.

## Piper has no voice for the active language

Open/use the Voice Library and install or import an appropriate Piper voice. The application should not silently fall back to an unrelated language voice.

## `mkdocs` is not recognized

Install the documentation dependencies:

```powershell
pip install -r requirements-docs.txt
```

Then retry:

```powershell
mkdocs serve
```

If the executable is still not on PATH, run:

```powershell
python -m mkdocs serve
```

## Documentation build reports a broken link

Run:

```powershell
mkdocs build --strict
```

Fix the referenced Markdown path or navigation entry before publishing.
