# v12.2.9 — Educational priorities and source safety limits

## Candidate Review

Review tiers now mean what a learner expects:

- **Recommended** — advanced vocabulary/grammar that is strongly central to the lesson/topic and reusable.
- **Useful** — solid normal vocabulary and expressions worth learning, but not a top-priority advanced topic item.
- **Optional** — niche, odd, document-specific, low-reusability, low-confidence, or overly long material.

The AI extraction response now includes educational review signals (`advancedness`, `topic_relevance`, `reusability`, `learning_value`, `document_specificity`). These fields organize review only; they do not decide how many candidates Smart Vocabulary extracts.

For large reviews, only Recommended candidates are selected by default. Users can explicitly select Recommended + Useful when they want a broader Queue.

## Material-size guardrails

Import Material still analyses the whole source in chunks without silently truncating it, but a single full-source run is now limited to at most 8 AI analysis parts. Word/character safeguards remain as additional protection. Book-sized sources must be narrowed to a selected chapter/section.

Candidate count remains content-driven: there is no target such as 60, 80, or 100 candidates.
