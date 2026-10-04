# Install the Windows EXE

## REQUIRED before you start

AI Anki Language Assistant does **not** replace Anki. To save, update, scan, or fix flashcards, you must have both of these installed:

1. **Anki Desktop** — [download Anki](https://apps.ankiweb.net/)
2. **AnkiConnect add-on** — [open AnkiConnect on AnkiWeb](https://ankiweb.net/shared/info/2055492159)

Install AnkiConnect inside Anki:

**Tools → Add-ons → Get Add-ons... → enter code `2055492159` → restart Anki**

!!! warning
    Keep **Anki Desktop running** while AI Anki Language Assistant is working with your decks. Without AnkiConnect, the app cannot communicate with Anki.

## Quick links — click here

If you do not know where to start, use these links:

| You need | Click here | Do you need it? |
|---|---|---|
| **OpenAI API key** | [OpenAI API Keys](https://platform.openai.com/api-keys) | **Recommended** — easiest setup |

**Recommended for most people:** use **OpenAI**.

This guide is for people who receive a ready-to-run Windows release and do **not** need Python, Git, a terminal, or programming knowledge.

## What you need

For normal flashcard creation, install or prepare only:

1. **AI Anki Language Assistant**
2. **Anki Desktop**
3. **AnkiConnect**
4. **one AI provider** — the recommended setup uses OpenAI

Speech recognition, local voices, OCR providers, and fully local AI are optional.

## 1. Install Anki Desktop

Download Anki from the official site:

[Download Anki Desktop](https://apps.ankiweb.net/)

Install it normally and open it once.

!!! important
    Keep **Anki Desktop open** while adding, updating, fixing, or scanning existing cards from AI Anki Language Assistant.

## 2. Install AnkiConnect

AI Anki Language Assistant communicates with Anki through the **AnkiConnect** add-on.

In Anki:

1. Open **Tools → Add-ons**.
2. Click **Get Add-ons...**
3. Enter the AnkiConnect code:

```text
2055492159
```

4. Confirm the installation.
5. Restart Anki.

Official add-on page:

[AnkiConnect on AnkiWeb](https://ankiweb.net/shared/info/2055492159)

## 3. Install AI Anki Language Assistant

Use the release supplied to you.

- If you receive a ZIP, extract it first.
- Keep the files together unless the release is explicitly marked as a single-file build.
- Start **AI Anki Language Assistant.exe**.

Windows SmartScreen can sometimes warn about newly distributed unsigned applications. If you trust the release source, open **More info** and continue.

You do **not** need to install Python for a packaged EXE release.

## 4. Create your Learning Profile

On the first launch, choose:

- **Learning language** — the language you are learning.
- **Level** — your approximate level.
- **Support language** — the language used for explanations and feedback.

![Learning Profile screen](../assets/profile.png)

These settings are reused throughout Create Card, Import Material, Queue, Conversation, STT, TTS, and feedback.

## 5. Use the recommended setup

For a first installation, continue with:

[Recommended setup](recommended-setup.md)

It uses **OpenAI** as the recommended AI provider.

You only need one API key. Other speech/audio features can be configured later if you want them.

## 6. First test

After configuration:

1. Keep Anki open.
2. Open **Create Card**.
3. Enter a simple vocabulary item such as `to put off`.
4. Generate the card.
5. Review it.
6. Add it to Anki.
7. Confirm that the note appears in Anki.

Then, if you want, test **Import Material** with lesson text, screenshots, or PDFs.

## Quick diagnosis

| Problem | What to check |
|---|---|
| Cannot connect to Anki | Anki is open and AnkiConnect is installed |
| No AI provider available | Add at least one API key in Setup |
| 401 / invalid API key | Recreate or re-enter the provider key |
| Microphone does not work | Windows microphone privacy permission |

For more details see [Troubleshooting](../troubleshooting/index.md).
