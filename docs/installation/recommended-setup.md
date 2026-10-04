# Recommended setup

## Before configuring AI

First install:

- **Anki Desktop:** [https://apps.ankiweb.net/](https://apps.ankiweb.net/)
- **AnkiConnect:** [https://ankiweb.net/shared/info/2055492159](https://ankiweb.net/shared/info/2055492159)

In Anki, install AnkiConnect via:

**Tools → Add-ons → Get Add-ons... → code `2055492159`**

Restart Anki afterwards and keep it open when using deck-related features.

For a non-technical Windows user, the recommended configuration is:

| Feature | Recommended provider |
|---|---|
| Setup mode | **Hybrid / BYOK** |
| AI card generation | **OpenAI** |
| Import / review / conversation AI | **OpenAI** |
| Speech-to-text | **Local Whisper** |
| Card audio / TTS | **Piper** |
| Flashcard storage | **Anki + AnkiConnect** |

This setup keeps the difficult AI work simple — one OpenAI key — while speech recognition and card audio can run locally without additional API charges.

## Why this setup

### One cloud account

The same OpenAI key can be used for generation, review, conversation, multimodal features, cloud STT, and OpenAI TTS when needed.

### Local speech recognition

Local Whisper uses **faster-whisper**. It does not require an API key.

The recommended model is:

```text
small
```

The model is loaded only when speech recognition is used. On a new computer, the first use can take longer while the model is downloaded and cached.

### Local audio

Piper provides free local TTS. Voices are managed from the application's **Speech & Audio / Voice Library** instead of requiring the user to edit configuration files manually.

## Step-by-step

### Step 1 — choose Hybrid / BYOK

Open:

**Setup → Hybrid / BYOK**

![Setup screen](../assets/setup.png)

### Step 2 — add the OpenAI API key

Create a key using the instructions in:

[API keys](api-keys.md#openai-recommended)

Paste the key into the OpenAI field in **Setup**, then reload configuration.

!!! note
    A ChatGPT subscription and OpenAI API billing are separate. Having ChatGPT Plus/Pro does not automatically add API credit.

### Step 3 — select Local Whisper

In **Setup → Speech-to-text**, choose:

```text
Local Whisper
```

Use:

```text
Model: small
Language: automatic / profile language
```

When Conversation first records speech, allow Windows microphone access if asked.

If Local Whisper is too slow on the computer, switch to **OpenAI Cloud STT**. It can reuse the same OpenAI API key.

### Step 4 — select Piper for audio

Open:

**Speech & Audio → Voice Library**

Then:

1. choose the current learning language,
2. preview an available Piper voice,
3. download the voice,
4. select it as the local TTS voice.

![Speech and Audio screen](../assets/audio.png)

If Piper is not convenient on a particular computer, use **OpenAI TTS** with the same OpenAI key.

### Step 5 — test Anki

Keep Anki Desktop running and confirm AnkiConnect is installed.

Create one test card and add it to Anki.

## Minimum working setup

If the user wants the fewest possible steps, this is enough:

```text
Anki Desktop
+ AnkiConnect
+ AI Anki Language Assistant
+ OpenAI API key
```

Speech and audio can be configured later.

## No-local-download alternative

For someone who does not want to download Whisper or Piper models:

| Feature | Provider |
|---|---|
| AI | OpenAI |
| STT | OpenAI Cloud |
| TTS | OpenAI |
| Anki | Anki + AnkiConnect |

This is the easiest configuration, but all AI/STT/TTS usage is cloud API usage.
