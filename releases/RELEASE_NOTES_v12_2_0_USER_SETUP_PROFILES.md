# v12.2.0 — Local / Hybrid / BYOK user setup

## Purpose

Turn the existing provider architecture into a user-facing setup that can be distributed without bundling private API keys.

## Changes

- Added a new **Setup** tab with three profiles:
  - Fully local
  - Hybrid / BYOK
  - API / BYOK
- The GUI can now start with no AI provider configured; first-time users are sent to Setup instead of crashing during configuration load.
- Added safe `.env` tooling:
  - create/update starter configuration;
  - import supported values from another `.env`;
  - backup the current `.env` before import;
  - open the local `.env`;
  - reload providers without restarting the app.
- Added non-secret status indicators for local and BYOK components.
- Added an Ollama reachability/model check from Setup.
- Added `AI_SETUP_MODE` routing:
  - local activates Ollama/Piper paths and ignores cloud provider keys;
  - hybrid activates all configured local + cloud providers;
  - api activates configured cloud AI/TTS providers while keeping local Whisper available.
- Cloud AI and TTS SDK imports are now lazy so the fully-local install does not require OpenAI/Gemini/Claude/ElevenLabs SDK packages.
- Import Material hides unconfigured cloud OCR choices and always keeps the local extraction path available.
- Added separate dependency sets:
  - `requirements-local.txt`
  - `requirements-hybrid.txt`
  - `requirements.txt` remains the full/hybrid alias.
- Updated README, `.env.example` and local-mode documentation for distribution/BYOK use.

## Secret handling

Clean releases still exclude `.env`, local backups, logs, caches, audio, runtime autosaves and API keys. Setup only reports whether a provider is configured; it does not display key contents.
