# Updating Existing Anki Cards

## Problem

Anki duplicate prevention is useful, but a learner may notice that a generated definition, translation, example, or collocation is wrong only after saving the card.

## Behaviour

When the same exact vocabulary expression or grammar sentence already exists in the selected deck, the application asks:

```text
Replace it with this reviewed version?
```

Choosing **Yes** updates all fields of the existing note. Choosing **No** leaves the note unchanged.

## Technical implementation

1. Search notes in the current deck and custom note type with `findNotes`.
2. Read note fields with `notesInfo`.
3. Compare the primary field exactly after normalising whitespace, HTML, and letter case.
4. Update the matching note through `updateNoteFields`.
5. Keep the same note ID and therefore preserve Anki scheduling and review history.

## Exact-match fields

- vocabulary cards: `Word`;
- grammar cards: `Sentence`.

The feature is available in both GUIs, Batch / Queue, Grammar, and Conversation-generated card flows.
