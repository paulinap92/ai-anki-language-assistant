# v10.6.1 — OCR short-list quality hotfix

Small Import Material hotfix on top of v10.6.

## Fixed

- The OCR quality gate no longer marks short, clean vocabulary lists as `Poor` only because they contain fewer than 20 words.
- Short word/phrase lists such as adjective lists are now treated as `Good` or `Medium` when the tokens look readable.
- `Look for words / phrases` now handles OCR output where a vocabulary table is flattened into space-separated words on one line, e.g.:

  ```text
  creepy fast-moving gripping haunting
  heart-warming heavy going implausible intriguing
  moving thought-provoking
  ```

  The local finder proposes individual candidates such as `creepy`, `fast-moving`, `gripping`, `haunting`, `heart-warming`, etc., instead of showing a poor-OCR warning or creating no useful rows.

## Notes

- This is still only a lightweight heuristic. It does not try to fully understand ambiguous two-word expressions; those can be fixed in cherry-pick/edit or with `Find from text with AI`.
