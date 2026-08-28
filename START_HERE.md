# Start here

AI Anki Language Assistant can run in three profiles from the **Setup** tab.

## Fully local

1. Install Python dependencies:

   ```powershell
   pip install -r requirements-local.txt
   ```

2. Install/start Ollama and pull a chat model.
3. Start Anki Desktop with AnkiConnect enabled.
4. Run:

   ```powershell
   python main_gui_custom.py
   ```

5. Open **Setup → Fully local → Create / update .env**.
6. Check/edit `OLLAMA_MODEL`, then click **Reload configuration** and **Check Ollama**. For Piper, you can now use **Speech & Audio → Voice Library** to preview/download voices directly; downloaded voices are stored under `PIPER_VOICE_DIR` (default `voices/piper`).

## Hybrid / BYOK

1. Install:

   ```powershell
   pip install -r requirements-hybrid.txt
   ```

2. Run the app and choose **Hybrid / BYOK** in Setup.
3. Either create a starter `.env` or click **Import .env** and select your existing configuration.
4. Paste only your own API keys into the local `.env`.
5. Click **Reload configuration**.

## API / BYOK

Use the same Hybrid dependency install, choose **API / BYOK**, and configure your own cloud provider keys. Local Whisper can still be used for Conversation speech input.

## Privacy

The clean release does not include `.env`, API keys, logs, caches, generated audio, Batch autosaves or Conversation rotation state. API keys stay in your local `.env` file.
