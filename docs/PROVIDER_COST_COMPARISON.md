# Provider Cost Comparison for AI Anki Language Assistant

Date checked: 2026-06-29

This file is a practical cost note for the current app workflow: vocabulary cards, grammar cards, Batch generation, and later audio generation.

The key point: for high-volume flashcard batches, Claude is not the best default provider. It is useful as an optional quality fallback, but it is relatively expensive and it does not provide the audio/TTS workflow used by this app.

---

## Current project defaults

These are the model defaults currently used by `.env.example` / `src/core/config.py`.

| Provider | Current default model | Input price / 1M tokens | Output price / 1M tokens | Audio/TTS in this app? | Practical verdict |
|---|---|---:|---:|---|---|
| Gemini | `gemini-2.5-flash` | $0.30 | $2.50 | Separate Gemini TTS may be configured, but text model is separate from audio | Good general batch provider, but not the cheapest Gemini option |
| OpenAI | `gpt-4.1-mini` | $0.40 | $1.60 | Yes, through separate OpenAI TTS settings, not through the text model itself | Good everyday option; cheaper output than Claude Haiku |
| Claude | `claude-haiku-4-5` | $1.00 | $5.00 | No Claude audio/TTS provider in this app | Too expensive as default for large batches; quality is not clearly better for ordinary sentence/vocabulary cards |

Sources:

- OpenAI model/pricing docs: https://developers.openai.com/api/docs/models/gpt-4.1-mini
- Gemini API pricing docs: https://ai.google.dev/gemini-api/docs/pricing
- Claude Haiku 4.5 pricing announcement: https://www.anthropic.com/news/claude-haiku-4-5
- Claude API pricing docs: https://platform.claude.com/docs/en/about-claude/pricing

---

## Cheaper model alternatives worth testing

The defaults above are not necessarily the cheapest choices. For big batches, these cheaper options are more sensible.

| Provider | Cheaper model candidate | Input price / 1M tokens | Output price / 1M tokens | Note |
|---|---|---:|---:|---|
| Gemini | `gemini-2.5-flash-lite` | $0.10 | $0.40 | Best candidate for cheap high-volume flashcard batches |
| OpenAI | `gpt-4o-mini` | $0.15 | $0.60 | Very cheap text model; good candidate for simple cards |
| OpenAI | `gpt-4.1-nano` | $0.10 | $0.40 | Cheapest OpenAI 4.1-family option; test quality before using for all cards |
| Claude | `claude-haiku-4-5` | $1.00 | $5.00 | This is already the cheap Claude option, but it is still much more expensive than cheap Gemini/OpenAI options |

Sources:

- Gemini 2.5 Flash-Lite pricing: https://ai.google.dev/gemini-api/docs/pricing
- GPT-4o mini pricing: https://developers.openai.com/api/docs/models/gpt-4o-mini
- GPT-4.1 nano pricing: https://developers.openai.com/api/docs/models/gpt-4.1-nano
- Claude Haiku 4.5 pricing: https://www.anthropic.com/news/claude-haiku-4-5

---

## Why Claude felt expensive here

Even with `claude-haiku-4-5`, Claude is expensive for this particular app because flashcard generation has a long structured output:

- definition,
- translation/explanation,
- example sentence,
- example translation,
- synonyms,
- collocations,
- grammar note,
- topic fit,
- quality fields,
- JSON structure.

The expensive part is usually output tokens. Claude Haiku output is $5.00 / 1M tokens, while `gpt-4.1-mini` output is $1.60 / 1M tokens, `gpt-4o-mini` output is $0.60 / 1M tokens, and `gemini-2.5-flash-lite` output is $0.40 / 1M tokens.

For ordinary vocabulary cards and normal example sentences, Claude quality is not clearly better enough to justify the extra cost. It may still be useful for difficult or ambiguous items, but not as the default batch engine.

---

## Rough cost example

This is only a rough estimate. Real costs depend on prompt length, generated output length, retries, regeneration, provider overhead, and whether the API returns token usage.

Assume one generated card uses roughly:

```text
4,000 input tokens
1,000 output tokens
```

Estimated cost per 1,000 cards:

| Model | Approx. cost / card | Approx. cost / 1,000 cards |
|---|---:|---:|
| `gemini-2.5-flash-lite` | $0.00080 | $0.80 |
| `gpt-4o-mini` | $0.00120 | $1.20 |
| `gpt-4.1-mini` | $0.00320 | $3.20 |
| `gemini-2.5-flash` | $0.00370 | $3.70 |
| `claude-haiku-4-5` | $0.00900 | $9.00 |

This explains why a small prepaid Claude balance can disappear quickly during Batch generation, especially if there are retries, regenerations, or validation false positives.

---

## Recommended provider policy for this project

### Default daily batch provider

Use one of these first:

```env
GEMINI_MODEL=gemini-2.5-flash-lite
```

or:

```env
OPENAI_MODEL=gpt-4o-mini
```

or, if quality is better in testing:

```env
OPENAI_MODEL=gpt-4.1-mini
```

### Quality fallback

Use Claude manually for difficult cards only:

```env
CLAUDE_MODEL=claude-haiku-4-5
```

Do not use Claude as the default provider for large batches unless cost is acceptable.

### Audio

Claude is not an audio provider in this project. Audio should stay separate:

```env
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=coral
```

or other configured TTS providers, depending on the app settings.

---

## Where to check real usage and costs

### OpenAI

- Usage dashboard: https://platform.openai.com/usage
- Billing overview: https://platform.openai.com/settings/organization/billing/overview
- Help article: https://help.openai.com/en/articles/10478918-api-usage-dashboard

### Anthropic / Claude

- Claude Console: https://console.anthropic.com
- In the Console, check Usage and Billing.
- Cost and usage reporting help: https://support.anthropic.com/en/articles/9534590-cost-and-usage-reporting-in-console
- API billing/credits help: https://support.anthropic.com/en/articles/8977456-how-do-i-pay-for-my-api-usage

### Gemini / Google

- Google AI Studio usage: https://aistudio.google.com/usage
- Gemini API billing docs: https://ai.google.dev/gemini-api/docs/billing
- Google Cloud Billing: https://console.cloud.google.com/billing

---

## Future app TODO

The app should eventually log real usage per call:

```text
provider=OpenAI model=gpt-4.1-mini input_tokens=... output_tokens=... estimated_cost=...
provider=Claude model=claude-haiku-4-5 input_tokens=... output_tokens=... estimated_cost=...
provider=Gemini model=gemini-2.5-flash-lite input_tokens=... output_tokens=... estimated_cost=...
```

It should also show a warning before large batches with expensive providers:

```text
You are about to generate 120 cards with Claude Haiku. This may be expensive.
Use Gemini Flash-Lite or OpenAI mini for cheaper batch generation.
```
