# v12.2.4 — Original Smart Vocabulary + Import modes restored

This release deliberately rolls back only the Import Material strategy changes that made Smart Vocabulary over-extract hundreds of candidates.

## Restored modes
- Provided examples
- Vocabulary
- Vocabulary + source examples
- Smart vocabulary
- Grammar
- Smart grammar import
- Mixed

## Smart Vocabulary behavior
The vocabulary extraction prompt is restored to the pre-v12.0.8 contract: explicit vocabulary and expression lists are kept, but normal prose is mined selectively rather than exhaustively. For continuous prose, Smart Vocabulary is instructed to stay at or below 80 candidates and prefer fewer high-quality reusable targets.

The Import Material text window is also restored to 24,000 characters for all modes.

All unrelated v12.2.3 fixes remain in place.
