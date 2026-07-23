# v8.1.5.14 — Provided Examples Validation Fix

Small regression fix for Batch mode: **Provided examples**.

## Fixed

- Local quality validation no longer treats the full raw row `target | sentence` as the expected word/phrase.
- It now validates only the left-side target:
  - expected: `microorganisms`
  - raw row can still be: `microorganisms | Bacteria are microorganisms which often cause disease.`
- Fixed the same issue for tab-separated rows:
  - `target<TAB>sentence`
- `Add all ready` now uses the same expected-target logic as preview/Add this card.
- Editing/revalidating a Provided examples card now also uses the parsed target, not the full raw row.

## Why

A valid card like:

```text
microorganisms | Bacteria are microorganisms which often cause disease.
```

was incorrectly blocked with:

```text
HARD: input phrase changed: expected 'microorganisms | Bacteria are microorganisms...', got 'microorganisms'.
```

That was a false positive.

## Tests

Added tests for:

- pipe-separated Provided examples rows
- tab-separated Provided examples rows
- no false HARD warning for `input phrase changed`
- no false HARD warning for example target usage
