# v12.0.3 test report

## Completed checks

- `python -m compileall` passed for `src`, `tests`, and all launchers.
- 26 focused Conversation / Anki deck / prompt / model / filtering / LangSmith tests passed.
- The focused tests cover:
  - topic-mode suggestions remaining unchanged,
  - separate flashcard-mode output fields,
  - exact deck-target duplicate rejection,
  - case, punctuation and article-only duplicate rejection,
  - longer collocations remaining valid,
  - unrelated candidate rejection,
  - staged-candidate rejection,
  - legacy provider compatibility,
  - selected Anki deck reading,
  - Basic `Front` / `Back` handling,
  - prompt JSON examples for both modes.

## Wider suite

Running the suite without the optional Claude and Gemini tests produced:

- 70 passed
- 2 skipped
- 3 failed

The same three failures are present in the unchanged v12.0.2 base archive and are unrelated to this release:

1. an older Batch Grammar prompt wording assertion,
2. an older Spanish synonym validator assertion,
3. an older Smart Grammar prompt wording assertion.

The complete suite cannot be collected in this environment because the optional `anthropic` and `google-genai` SDKs are not installed. The project requirements still declare both dependencies.

## GUI limitation

The code compiles, but the window was not rendered in this environment because `customtkinter` is not installed here. A Windows smoke test should verify the final panel sizing and interaction with a live Anki / AnkiConnect instance.
