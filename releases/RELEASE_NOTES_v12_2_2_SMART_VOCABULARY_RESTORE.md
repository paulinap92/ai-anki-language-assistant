# v12.2.2 — Smart Vocabulary restore

This release reverses the Import Material behavior regression introduced by the v12.1.1 UI simplification.

## Import Material

The user-facing modes are now:

- `Smart vocabulary` — recommended/default; restores the original smart vocabulary extraction contract.
- `Vocabulary` — strict vocabulary-only extraction.
- `Grammar` — routes to Smart grammar import.
- `Auto` — routes to Mixed classification.

`Examples / sentences` is no longer exposed as an AI import mode because it routed to the much narrower `Provided examples` contract and could return only a small subset of a rich lesson.

## Smart vocabulary behavior

Smart vocabulary scans the entire imported lesson, including content outside explicit vocabulary lists, and may preserve strong exact source examples when they genuinely improve the learning candidate. It does not turn the import into a sentence-only extraction task.

`Provided examples` remains available for already-clean `target | sentence` input in the Batch/Queue workflow.

The v12.2.1 Conversation Practice topic-isolation and tutor-audio fixes are preserved.
