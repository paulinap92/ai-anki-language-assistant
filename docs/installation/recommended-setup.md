# Recommended setup

## Before configuring AI

First install:

- **Anki Desktop:** [https://apps.ankiweb.net/](https://apps.ankiweb.net/)
- **AnkiConnect:** [https://ankiweb.net/shared/info/2055492159](https://ankiweb.net/shared/info/2055492159)

In Anki:

**Tools → Add-ons → Get Add-ons... → code `2055492159`**

Restart Anki afterwards and keep it open when using AI Anki Language Assistant.

## Recommended setup for most users

You need:

1. **Anki Desktop**
2. **AnkiConnect**
3. **AI Anki Language Assistant**
4. **one OpenAI API key**

That is all you need to start creating and saving cards.

## Step 1 — create an OpenAI API key

Open:

[OpenAI API Keys](https://platform.openai.com/api-keys)

Then:

1. sign in,
2. click **Create new secret key**,
3. copy the key.

!!! note
    ChatGPT subscriptions and OpenAI API billing are separate. Having ChatGPT Plus/Pro does not automatically include API credit.

## Step 2 — paste the key into the app

Open:

**Setup → Recommended setup**

Paste the OpenAI API key and click:

**Apply recommended setup**

You do **not** need to open or edit `.env` manually. The application saves the key locally for you.

![Setup screen](../assets/setup.png)

## Step 3 — test Anki

Keep **Anki Desktop open**.

1. Open **Create Card**.
2. Enter a simple word or phrase.
3. Generate the card.
4. Review it.
5. Add it to Anki.
6. Confirm that the card appears in your Anki deck.

If that works, the basic installation is complete.

## Gemini instead of OpenAI

Gemini is optional.

If you prefer Google Gemini, create a key here:

[Google AI Studio API Keys](https://aistudio.google.com/apikey)

Then add it in **Setup** instead of OpenAI.

## Optional features

Speech recognition, local voices, cloud speech services, OCR providers, and fully local AI are **optional**. You do not need to configure them to start using the application.
