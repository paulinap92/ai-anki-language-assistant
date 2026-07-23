# v9.1.8 — Import grammar sends sentences to Batch

Small stability/UX patch after v9.1.7.

## Changed

- In Import Material, grammar marking now means: **send this selected sentence/fragment to Grammar Batch**.
- Import Material no longer tries to create or guess a grammar target when the user marks an item as grammar.
- Per-card action label changed from `As grammar` to `To Grammar Batch`.
- Bulk action label changed from `Selected → grammar` to `Selected → Grammar Batch`.
- Sending Import candidates to Batch no longer creates duplicated rows like `sentence | same sentence` for grammar items.

## Expected flow

1. Extract text from PDF/image/TXT/HTML.
2. Find sentences or select useful fragments.
3. Mark selected items with `To Grammar Batch` / `Selected → Grammar Batch`.
4. Send selected candidates to Batch / Queue.
5. Batch mode `Grammar` identifies the grammar focus from the sentence and generates the card.

## Not changed

- Word/phrase extraction remains available.
- Sentence/provided-example extraction remains available.
- Optional AI assist remains available.
- Manual candidate builder remains available.
