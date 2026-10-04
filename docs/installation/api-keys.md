# API keys

You do **not** need every provider.

For the recommended setup, create **one OpenAI API key**. Other providers are optional alternatives.

Never send an API key to another person, paste it into a public issue, or commit it to GitHub.

## OpenAI — recommended

1. Open the official OpenAI API key page:
   [OpenAI API keys](https://platform.openai.com/api-keys)
2. Sign in.
3. Create a new secret key.
4. Copy it immediately and store it somewhere private.
5. Open **AI Anki Language Assistant → Setup**.
6. Paste it into **OpenAI API Key**.
7. Reload configuration.

OpenAI API usage is billed separately from ChatGPT subscriptions. If API requests are rejected because no API balance/billing is available, configure billing in the OpenAI Platform account.

[OpenAI API quickstart](https://platform.openai.com/docs/quickstart)

!!! warning
    Do not share the key. If a key is exposed, revoke it in the provider dashboard and create a new one.

## Gemini

Gemini is an alternative AI and multimodal provider.

1. Open Google AI Studio:
   [Create a Gemini API key](https://aistudio.google.com/apikey)
2. Create or select a project.
3. Create an API key.
4. Copy it.
5. Paste it into **Setup → Gemini API Key**.
6. Reload configuration.

[Official Gemini API key guide](https://ai.google.dev/gemini-api/docs/api-key)

## Groq

Groq can be used both for LLM features and **Groq Cloud STT**.

1. Open:
   [Groq API Keys](https://console.groq.com/keys)
2. Sign in.
3. Click **Create API Key**.
4. Copy the key.
5. Paste it into **Setup → Groq API Key**.
6. Reload configuration.

The same key can be reused if **Groq Cloud STT** is selected.

## OpenRouter

OpenRouter is an optional OpenAI-compatible provider and can route requests to multiple models.

1. Open:
   [OpenRouter Developers](https://openrouter.ai/developers)
2. Create an account.
3. Create an API key from the dashboard.
4. Paste it into **Setup → OpenRouter API Key**.
5. Reload configuration.

The application defaults to the configured OpenRouter model, including free-model routing when selected.

## Claude / Anthropic

Claude is optional.

Create a key from the Anthropic Console and paste it into **Setup → Anthropic / Claude API Key**.

[Anthropic Console](https://console.anthropic.com/)

## Mistral OCR

Mistral is optional and is used for OCR/import workflows when configured.

Create a Mistral API key and enter it in **Setup → Mistral API Key**.

## ElevenLabs

ElevenLabs is optional and used only for TTS/voice generation.

If you do not need ElevenLabs voices, leave it unconfigured and use Piper, OpenAI TTS, or Gemini TTS instead.

## Which key should I create?

| Goal | Key |
|---|---|
| Simplest recommended setup | **OpenAI** |
| Gemini ecosystem / multimodal | Gemini |
| Fast cloud STT + optional LLM | Groq |
| Free-model routing / many providers | OpenRouter |
| Claude models | Anthropic |
| Dedicated OCR | Mistral |
| Dedicated premium voices | ElevenLabs |

Start with **one key**, test the application, and add other providers only if you actually need them.
