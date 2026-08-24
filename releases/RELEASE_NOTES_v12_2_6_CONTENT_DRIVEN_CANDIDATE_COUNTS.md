# v12.2.6 — Content-driven candidate counts

Import Material no longer aims for a fixed number of candidates.

## What changed

- Smart Vocabulary no longer targets or truncates to ~80 items.
- Candidate count is based on the source: a simple page can yield 1–5 useful items, while a dense lesson or glossary can legitimately yield 100+ items.
- Long sources are still analysed completely in chunks, then merged and deduplicated.
- The merged result is not cut to a fixed whole-document quota.
- The same no-quota rule now applies to Smart Grammar, Mixed/general candidate extraction and direct multimodal candidate extraction.
- Import Material tells the user that there is no fixed candidate count.

## Quality rule

The model should return every genuinely useful reusable candidate, but must not mine every ordinary word from prose or add weak candidates merely to increase the count.

## Runtime safety

A high single-response runaway guard remains only to prevent malformed provider output from trying to render thousands of rows in the desktop UI. It is not passed to the model and does not define normal extraction size.
