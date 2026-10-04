# API keys

You do **not** need every provider.

For the recommended setup, create **one OpenAI API key**. Other providers are optional alternatives.

Never send an API key to another person, paste it into a public issue, or commit it to GitHub.

## OpenAI — recommended

**CLICK HERE:** [Create / manage an OpenAI API key](https://platform.openai.com/api-keys)

Do this:

1. Click the link above.
2. Sign in or create an OpenAI Platform account.
3. Click **Create new secret key**.
4. Copy the key immediately.
5. Go back to **AI Anki Language Assistant → Setup**.
6. Paste the key into the **Recommended setup** box.
7. Click **Apply recommended setup**.

That is enough for the recommended AI configuration.

!!! important "ChatGPT subscription is not the same as API access"
    ChatGPT Plus/Pro and OpenAI API billing are separate products. If the API account has no billing/credit available, the app can receive a billing or quota error even if ChatGPT itself works.

Official links:

- [OpenAI API keys](https://platform.openai.com/api-keys)
- [OpenAI API pricing](https://platform.openai.com/pricing)

OpenAI API usage is billed separately from ChatGPT subscriptions. If API requests are rejected because no API balance/billing is available, configure billing in the OpenAI Platform account.

[OpenAI API quickstart](https://platform.openai.com/docs/quickstart)

!!! warning
    Do not share the key. If a key is exposed, revoke it in the provider dashboard and create a new one.

## Gemini — easy alternative to OpenAI

Gemini is optional. Use it if you prefer Google instead of OpenAI.

**CLICK HERE:** [Create a Gemini API key in Google AI Studio](https://aistudio.google.com/apikey)

Do this:

1. Click the link above.
2. Sign in with a Google account.
3. Create an API key in Google AI Studio.
4. Copy it.
5. Open **AI Anki Language Assistant → Setup**.
6. Paste it into the Gemini API key field.
7. Reload configuration.

Official help:

- [Google: Using Gemini API keys](https://ai.google.dev/gemini-api/docs/api-key)
- [Google: Gemini API getting started](https://ai.google.dev/gemini-api/docs/get-started)

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
