# v11.2.2 — Audio / Visible Sentence Alignment Hotfix

## Why

The Speech / Audio scan could select `ContextExample` as the audio source while the learner-visible grammar card sentence was a different full sentence. This created a bad review experience: the user read one sentence but heard another.

Example bad row:

```text
[ready] I haven't the time to go to the bank. · AI Grammar Light Card · Source: ContextExample → Target: Audio — I can't join you now because I haven't the time to spare.
```

## Changes

- In automatic audio source selection, grammar cards now prefer the visible `Sentence` / `Word` / `Front` field when it already looks like a complete sentence.
- `ContextExample` remains preferred for word/phrase/connector cards where the visible top item is only a target, not a complete sentence.
- Grammar generation prompt now explicitly avoids two competing examples: if `sentence` is a full learner-visible example, `context_example` must be the same sentence or include it unchanged.
- Source-focus guard now aligns generated grammar cards when both `Sentence` and `ContextExample` are complete but different examples:
  - source OCR sentence wins when provided;
  - otherwise the better Natural Context can be promoted to `Sentence` so visible text and audio match.

## Rule

```text
No hidden audio mismatch:
if the card shows a full sentence, automatic audio reads that same sentence.
```

For target-only cards, e.g. `therefore` or `to have it out with sb`, Natural Context can still be used as the audio source.
