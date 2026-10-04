# AI Providers

AI providers are isolated behind the shared AI client interface and created by `src/ai/factory.py`. The GUI receives already-configured clients instead of constructing provider SDKs itself.

## Current providers

| Provider | Status | Configuration |
|---|---|---|
| Gemini | Available | `GEMINI_API_KEY` |
| OpenAI | Available | `OPENAI_API_KEY` |
| Claude | Available | `ANTHROPIC_API_KEY` or `CLAUDE_API_KEY` |
| Ollama | Available | `OLLAMA_MODEL` + local Ollama |
| Groq | Available | `GROQ_API_KEY` |
| OpenRouter | Available | `OPENROUTER_API_KEY` |

Cloud SDK imports are lazy, so a local-only installation does not need every cloud SDK at runtime.

## Availability rule

A provider without its required configuration should not appear as a normal selectable provider.

For example:

```text
no OPENAI_API_KEY
→ no OpenAI AI client

GEMINI_API_KEY configured
→ Gemini can be created when cloud providers are allowed

OLLAMA_MODEL configured + local/hybrid mode
→ Ollama can be created

OPENROUTER_API_KEY configured
→ OpenRouter can be created

GROQ_API_KEY configured
→ Groq can be created
```

!!! important "Architecture rule"
    Provider-specific SDK setup belongs in provider modules and factories, not in the GUI. New providers should implement the common interface and be registered centrally.

See [Adding an AI Provider](../developer-guide/adding-provider.md).
