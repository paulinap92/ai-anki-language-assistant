# Environment configuration

Runtime/provider configuration is loaded from a local `.env` file. Start from the repository example:

```powershell
Copy-Item .env.example .env
```

!!! danger "Do not commit secrets"
    Real API keys belong only in your local `.env`. The repository tracks `.env.example`, not your private configuration.

## Setup profiles

`AI_SETUP_MODE` controls which provider families may be loaded:

| Value | Purpose |
|---|---|
| `local` | Local providers only, such as Ollama and Piper |
| `hybrid` | Local + configured BYOK cloud providers |
| `api` | Configured BYOK cloud providers |

Example:

```env
AI_SETUP_MODE=hybrid
```

If no valid mode is supplied, the application derives a sensible setup from the configured local/cloud providers and still allows the GUI to start for first-time setup.

## Core settings

```env
ANKI_CONNECT_URL=http://localhost:8765
ANKI_DECK_NAME=AI Vocabulary
DEFAULT_TARGET_LANGUAGE=English
AUDIO_CACHE_DIR=.audio_cache
```

The Learning Profile is separate from provider configuration. Learner language, level, and support language are stored in `user_profile.json` and should remain the single source of truth for learner-facing language behavior.

## Provider availability

Empty values and common placeholder values are treated as unconfigured. A cloud provider should only become available when its required API key is actually present and the active setup profile allows cloud providers.

See:

- [AI Providers](ai-providers.md)
- [Speech-to-Text](stt.md)
- [Text-to-Speech](tts.md)
