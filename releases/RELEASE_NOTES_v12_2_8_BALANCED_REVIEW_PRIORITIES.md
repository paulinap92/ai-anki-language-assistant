# v12.2.8 — Balanced candidate review priorities

Candidate Review no longer promotes nearly every Smart Vocabulary result to Recommended.

## What changed

- Recommended is now intentionally conservative.
- Explicit lesson vocabulary/expression sections and highlighted items are Recommended.
- Strong idioms may also be Recommended when confidence is high.
- Generic reading-text phrases, collocations, grammar candidates, provided examples and candidates with a valid source sentence default to Useful.
- Low-confidence, review-needed, very long and obvious document-specific/named-entity candidates stay Optional.
- Review priority only organizes the UI; it does not remove candidates or change Smart Vocabulary extraction.

This fixes the regression where a long import could show effectively 100% of candidates as Recommended, making the three-tier review useless.
