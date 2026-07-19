# v8.1.4.2 — Quality Validator Sanity Hotfix

This hotfix reduces noisy validation warnings and makes hard quality problems block Anki writes.

## Fixed

- Polish diacritics are now valid in Polish translation/example/grammar fields.
  - `ó` is Polish too; it no longer triggers Spanish-looking warnings.
- Noisy provider warnings are filtered when they are known false positives:
  - `Spanish-looking characters detected in Polish ...`
  - `possible mixed-language text in Polish grammar note: a/the/on/for...`
- Polish grammar notes can contain quoted English articles/prepositions/phrases without mixed-language warnings.
- Exact-input validation ignores outer quotes around user inputs:
  - `"Nevertheless…"` matches `Nevertheless…`.
- Hard quality warnings now block Add to Anki / Add all ready until the card is edited.
  - Example: Cyrillic in a Polish field is blocked before Anki write.

## Regression cases

- `inflacja dyplomów` / `Ze względu...` → no Spanish-looking warning.
- grammar note containing `'a'`, `'the'`, `'for'` → no mixed-language warning.
- `талентах` in Polish translation → hard warning and blocked Anki write.
- `"Nevertheless…"` input vs `Nevertheless…` generated phrase → accepted.
