# v12.4.6 — Global duplicate guard

## Why this fix exists

The application already had duplicate protection, but the protection was split across workflows and no longer matched the current card model.

Two concrete regressions were found:

1. Grammar became target-first in v12.4.4, while duplicate identity was still sentence-based. The same grammar target could therefore be added repeatedly when the generated example sentence changed.
2. Some final add paths checked only the active deck, while Batch prechecks scanned the whole Anki collection. A card could pass one path and still be duplicated through another.

Import Material also deduplicated whole candidate rows (`target + sentence`) rather than the final card identity, so one target with several source sentences could fan out into repeated Queue work.

## Fixed identity rules

- Vocabulary: one card per lexical target (`Word`) across the Anki collection.
- Provided examples: same identity as Vocabulary; the source sentence is context, not a second identity.
- Grammar: one card per target-first `Target` across the Anki collection. The example sentence no longer defines duplicate identity.
- Legacy vocabulary note types are included in the collection-wide vocabulary check but are never overwritten automatically.

## Safety changes

- Final Vocabulary adds now perform a collection-wide duplicate guard.
- Batch's old `add_card_without_duplicate_scan` fast path keeps a final current-model duplicate guard instead of blindly writing.
- Grammar add/update searches the entire collection and matches the target-first `Target`, with a Structure fallback only for older grammar notes whose Target is empty.
- Queue can precheck a reliable Grammar target before calling the AI provider.
- Import candidate deduplication and Queue deduplication use the same final card identity instead of the full source row.
- Vocabulary and Provided Example candidates with the same target collapse to one card identity.

## Regression tests

Added tests for:

- legacy vocabulary duplicate in another deck;
- Batch final guard after precheck;
- same Grammar target with different example sentences;
- same example sentence under a different Grammar target;
- duplicate Import candidates with different source sentences;
- Vocabulary + Provided Example identity alignment;
- Queue identity alignment;
- Grammar duplicate precheck before provider generation.

Targeted duplicate/import/grammar regression suite: 58 passed.

The complete project test collection cannot run in this execution environment because optional provider SDKs (`anthropic` and `google.genai`) are not installed; this is an environment dependency issue, not a failing application test.
