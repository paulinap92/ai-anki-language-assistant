# v11.5.11 — Separate Vision OCR from Image Candidate Extraction

## Goal

Fix the Import Material multimodal flow so image/PDF Vision OCR behaves like OCR only.

Before this release, choosing OpenAI/Gemini multimodal import from the OCR method dropdown could read the image and immediately create structured candidate drafts. That mixed two different user intentions: transcribing a screenshot and extracting flashcard candidates.

## What changed

- Renamed the visible multimodal OCR options to:
  - `OpenAI Vision OCR (text only)`
  - `Gemini Vision OCR (text only)`
- The main OCR/import button now runs `image/PDF -> transcribed text` only for these methods.
- The result is placed into the Import Material reviewed text box.
- Existing candidate cards are cleared to avoid confusing old candidates with new OCR text.
- The user must explicitly click `Find candidates with selected strategy` to run AI candidate extraction from the reviewed text.
- Added `build_multimodal_ocr_prompt()` with strict OCR-only instructions.
- Added `extract_text_with_multimodal()` as the text-only vision OCR service entry point.

## Strict Vision OCR contract

Vision OCR must:

- extract only visible text;
- preserve headings, bullets, numbering, line breaks and tables;
- keep tables as Markdown when possible;
- preserve slash alternatives, accents and punctuation;
- mark unreadable fragments as `[unclear]`;
- return only the transcription.

Vision OCR must not:

- create flashcards;
- create candidate JSON;
- classify vocabulary/grammar/provided examples;
- translate hidden meaning;
- summarize or explain grammar;
- complete exercises or generate examples.

## Correct workflow

```text
Load image / screenshot / PDF
→ Run OpenAI/Gemini Vision OCR
→ review/clean OCR text
→ click Find candidates with selected strategy
→ review candidates
→ send selected items to Batch
```

## Notes

The older direct image-to-candidate helper is kept as an advanced compatibility method in code, but it is no longer used by the normal OCR button path.
