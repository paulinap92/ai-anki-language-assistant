# v11.5.1 — LLMOps token and cost summary

Small observability update for demo/provider comparison.

## Added

- Captures provider token usage when available from OpenAI, Gemini, and Claude API responses.
- Sends LangSmith-friendly provider/model metadata:
  - `ls_provider`
  - `ls_model_name`
  - `usage_metadata`
- Adds fallback token estimates when provider usage is unavailable.
- Adds optional local estimated-cost calculation from `.env` rates.
- Adds TTS cost metadata for audio generation, including ElevenLabs/OpenAI/Gemini character counts and cache hits.
- Adds a simple LLMOps tab cost summary:
  - last costed run;
  - current session events;
  - total tokens;
  - estimated session cost;
  - TTS cache hits.

## Notes

- Costs are estimates, not billing statements.
- If no rates are configured in `.env`, the app still shows token estimates and says the rate is not configured.
- LangSmith can show token/cost metadata when provider/model and usage data are available.
