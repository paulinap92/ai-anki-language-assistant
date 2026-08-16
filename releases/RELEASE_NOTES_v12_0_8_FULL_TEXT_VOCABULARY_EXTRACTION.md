# v12.0.8 - Full-text vocabulary candidate extraction

## Purpose
Restore the intended Vocabulary import behavior after a regression made the AI stop too close to explicit lesson vocabulary sections.

## Changes
- Explicit `Vocabulary`, `Key Terms`, `Expressions`, `Idioms`, `Lexique` and similar lists are still extracted completely first.
- Those lists are now a guaranteed minimum, not the finish line.
- The AI must continue through the complete remaining lesson and find additional reusable vocabulary in prose, facts, examples, warm-ups, discussion questions, explanations and homework.
- Advanced C1/C2 material explicitly asks for advanced lexical chunks and academic/discussion language outside the official vocabulary boxes.
- Discussion questions are no longer discarded wholesale; their useful language may be extracted while numbering, blanks, answer labels and instructions are ignored.
- Removed the former `keep reading-text mining minimal` / `small, selective set` behavior that caused rich lessons to collapse to a handful of candidates.
- Vocabulary-family AI text input limit is now 60,000 characters instead of 24,000 characters.
- TXT/HTML remains local extraction, not OCR: HTML markup is stripped locally and the resulting text goes to the normal AI candidate finder.

## Regression case
A C1 lesson containing 8 explicit Key Terms and 6 Common Expressions previously produced exactly 14 Vocabulary candidates even though the rest of the lesson contained many useful phrases and collocations. v12.0.8 changes the extraction contract so those 14 explicit items are the guaranteed base and full-text mining continues afterward.
