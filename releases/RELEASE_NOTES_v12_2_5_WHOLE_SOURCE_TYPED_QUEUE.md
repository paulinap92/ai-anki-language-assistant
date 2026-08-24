# v12.2.5 — Whole-source Import Material + typed Queue

This release fixes two data-flow problems found during real lesson imports.

## Whole source is analysed

Import Material no longer truncates AI input at 24,000 characters. After material is read or OCR is complete, the UI shows the source size and how many AI parts will be used. Long text is split, analysed part-by-part, merged and deduplicated.

Smart Vocabulary keeps the mature selective behavior: explicit vocabulary/expression sections are preserved first, while continuous prose is globally limited to a useful result set instead of returning hundreds of candidates per chunk.

## Candidate type belongs to the item

Vocabulary, Grammar and Provided Example are now preserved per candidate from Import Material into Queue. The Queue-wide Input type selector is only for manually loaded clean files and cannot overwrite imported item types.

Each candidate card has a visible Type dropdown, so changing a row to Grammar produces an immediate visible change before it reaches Queue.

## Vocabulary source examples

Smart Vocabulary can preserve a useful source sentence without converting the item to Provided Example. If imported text is actually a glossary definition and does not use the target, it is stored only as source definition/context and Queue generates a real usage example.
