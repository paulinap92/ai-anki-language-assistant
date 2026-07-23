# Practice and Print Mode

The modern GUI includes a `Practice & Print` tab that reads supported notes from the selected Anki deck through AnkiConnect.

## Supported Anki note types

- `AI Vocabulary Light Card`
- `AI Grammar Light Card`

The application uses the stored Anki fields rather than asking the LLM to recreate the learning material.

## Card scope

Available card scopes:

- all supported cards in the selected deck,
- due and overdue cards,
- overdue cards,
- new cards.

After loading, cards are shown with checkboxes. The learner selects the material, while the application randomizes only the question order.

## Interactive practice

Vocabulary cards use the example sentence where possible:

```text
She was ________ to accept the offer.
```

The application creates four answer options. It prefers distractors with the same part of speech from the selected material. If the exact word or phrase is not present in the stored example, the question falls back to the stored definition.

Grammar cards ask the learner to identify the structure used in the stored sentence.

The interaction is non-blocking:

1. select an answer;
2. run `Check`;
3. review inline feedback;
4. continue with `Next`;
5. finish with `End session` or after the final question.

## Printable test

`Create printable test + key` writes two standalone HTML files:

- `<deck>_test.html`
- `<deck>_answer_key.html`

Both files are print-friendly. They can be printed directly from a browser or saved as PDF using the browser's print dialog.

## Design limitations of the first version

- Distractors are selected locally from the chosen cards; no LLM call is made.
- A vocabulary gap requires the exact word or phrase to occur in the stored example.
- The first version does not modify Anki scheduling or mark cards as reviewed.
- Practice results are session-only and are not yet stored.
