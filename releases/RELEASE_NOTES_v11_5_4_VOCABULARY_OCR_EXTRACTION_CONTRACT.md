# v11.5.4 — Vocabulary OCR Extraction Contract

## Purpose
Make Import Material reliable for vocabulary-heavy lesson pages, not only Smart Grammar pages.

## Changes
- Add a focused vocabulary-only OCR/import prompt.
- Add new Import Material modes:
  - `Vocabulary + source examples`
  - `Smart vocabulary`
- In vocabulary extraction modes, force all AI candidates to remain `type="vocabulary"`.
- Prevent AI providers from mixing `provided_example` or `grammar` into Vocabulary mode.
- Extract explicit lesson vocabulary lists by recall, not by top-N selection.
- Prioritize headings such as `Vocabulario`, `Léxico`, `Vocabulary`, `Expresiones`, and `Expresiones coloquiales`.
- Split slash-separated word lists into separate vocabulary candidates.
- Preserve/expand alternatives in fixed expressions such as `poner la carne / piel de gallina`.
- Keep source examples as vocabulary context metadata, not as Provided Examples mode.
- Preserve metadata such as `candidate_kind`, `source_section`, `source_type`, `strategy`, `reason`, and `confidence`.

## Why
Generic OCR candidate extraction was too random for vocabulary lessons: providers returned different mixes, skipped many explicit list items, and sometimes changed vocabulary examples into Provided Examples.
