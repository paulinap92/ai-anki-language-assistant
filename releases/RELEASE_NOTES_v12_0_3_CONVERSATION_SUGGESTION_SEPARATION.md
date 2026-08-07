# v12.0.3 — Conversation suggestion separation

## Problem fixed

Flashcard-based Conversation previously reused the topic-mode `suggested_vocabulary` list. As a result, expressions already present in the selected Anki deck could be displayed and staged as though they were new flashcards.

## New workflow

### Talk about a topic

The existing workflow stays unchanged: AI may suggest useful vocabulary and the learner can edit and stage it for Batch / Queue.

### Talk based on flashcards

The side panel now separates:

1. **Flashcards in this session** — read-only practice material selected from the deck or Batch.
2. **Expressions to use next** — speaking cues for the next answer; these may reuse existing targets.
3. **New flashcard candidates** — only genuinely new expressions that may be edited and staged.

## Filtering rules

- Exact existing deck/session targets are rejected as new candidates.
- Case, punctuation and article-only variants are also rejected.
- Already staged expressions are not proposed again.
- A longer collocation may remain valid, for example `impartir una clase magistral` when `clase magistral` already exists.
- New candidates must be grounded in the current answer, correction, improved answer, mini-practice or tutor reply.
- `next_question` is deliberately excluded from grounding so the model cannot inject a random expression merely to justify a suggestion.
- Legacy providers that still return only `suggested_vocabulary` are treated safely: in flashcard mode those values become practice cues, not new cards.

## Tests

The release adds prompt, model and pure filtering regression tests covering duplicates, longer collocations, staged items and unrelated candidates.
