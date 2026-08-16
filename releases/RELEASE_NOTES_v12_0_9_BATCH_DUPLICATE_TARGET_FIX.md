# v12.0.9 — Batch Vocabulary Duplicate Target Fix

## Purpose
Make the duplicate check before AI generation use the same vocabulary target as the later Anki write.

## Fixed flow
For vocabulary and vocabulary-with-source-sentence rows, duplicate identity is only the lexical target versus Anki's `Word` field.

Example:

```text
Batch row: echo chamber | Social media can create an echo chamber.
Duplicate key: echo chamber
Anki field checked: Word
```

The source sentence is context for card generation and never participates in vocabulary duplicate matching.

## Behaviour
- `provided_target` is preferred when Import Material already separated target and sentence.
- `target | sentence` and `target<TAB>sentence` use only the target side.
- Plain vocabulary phrases use the full phrase unchanged.
- Sentence-only Provided Examples skip pre-generation Word matching because no reliable lexical target exists yet.
- Pre-generation, Add-all summary and final add/update use the same persisted target.
- Grammar duplicate handling is unchanged and remains Sentence-based.
