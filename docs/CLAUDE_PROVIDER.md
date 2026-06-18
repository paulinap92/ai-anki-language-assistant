# Claude Provider

Claude is available as a third cloud provider alongside Gemini and OpenAI.

## Setup

Install dependencies:

```bash
pipenv install
```

Add the following values to `.env`:

```env
ANTHROPIC_API_KEY=your_real_key
CLAUDE_MODEL=claude-haiku-4-5
```

Claude appears automatically in the provider selector when
`ANTHROPIC_API_KEY` is configured.

## Supported flows

The provider implements the same application contract as Gemini and OpenAI:

- vocabulary generation,
- validation and exact-input preservation,
- sentence-first grammar analysis,
- conversation start,
- conversation feedback,
- Batch / Queue generation,
- Practice and Print workflows that use generated Anki cards.

## Implementation notes

The integration uses the Anthropic Messages API. Responses contain content
blocks, so the client joins only blocks whose type is `text`. JSON parsing and
Pydantic validation remain centralized in `VocabularyAiClient`.

The default model is `claude-haiku-4-5` because this application benefits from
a fast, lower-cost model for repeated structured generations. The model can be
changed through `CLAUDE_MODEL` without modifying the source code.
