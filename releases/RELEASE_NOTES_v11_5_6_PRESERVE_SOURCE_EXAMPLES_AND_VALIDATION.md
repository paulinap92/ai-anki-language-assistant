# v11.5.6 — Preserve source examples and pattern-aware validation

## Fixed

- Vocabulary candidates with imported source examples are now routed to the sentence-based Batch prompt as `target | source sentence`, so the model preserves the imported example instead of generating a new one.
- Import Material still shows these as vocabulary candidates; the internal Batch mode switches to Provided examples only to protect the source sentence and avoid wasted provider calls.
- Vocabulary + source examples and Smart Vocabulary prompts now tell the model to complete obvious gap-fill source sentences before attaching them as examples, and to mark such candidates as review-needed.
- Local quality validation no longer raises a HARD warning for pattern-style targets such as `pensar en (alguien/algo)` when the example uses an inflected realization like `pienso en`. It now downgrades uncertain pattern checks to SOFT review warnings.

## Expected behavior

`dar gato por liebre` with a source sentence from Import Material should enter Batch as:

```text
dar gato por liebre | ¡Esta hamburguesa es mucho más pequeña que la del anuncio! ¡Nos han vuelto a dar gato por liebre!
```

The generated card should preserve that example instead of inventing a new one.
