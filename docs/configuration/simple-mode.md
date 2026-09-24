# Simple Mode

!!! warning "Planned feature"
    `SIMPLE_MODE` is part of the product plan but is **not implemented in the current v12.4.8 codebase**. Do not expect `SIMPLE_MODE=true` to change the GUI yet.

The intended configuration is:

```env
SIMPLE_MODE=true
```

The goal is to reduce technical choices for less technical users while reusing the same provider factories and application workflows.

## Intended behavior

Simple Mode should expose only useful, actually configured choices.

Examples:

```text
no ELEVENLABS_API_KEY
→ ElevenLabs hidden

no OPENAI_API_KEY
→ OpenAI cloud features hidden

only GROQ_API_KEY
→ once Groq is implemented, the user should mainly see Groq-compatible choices
```

## Design constraint

Simple Mode must be a presentation/configuration layer, **not a second application architecture**. It should preserve:

- the Learning Profile as the language source of truth,
- provider factories,
- validation,
- duplicate protection,
- Queue/review,
- human approval before Anki.

When the feature is implemented, update this page together with the code and regression tests.
