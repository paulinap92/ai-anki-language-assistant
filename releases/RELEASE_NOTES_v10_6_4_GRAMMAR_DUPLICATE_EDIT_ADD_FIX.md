# v10.6.4 — Grammar duplicate guard + edited card add UX hotfix

## Why

The Batch/Queue grammar flow had two bad UX behaviours:

1. Grammar rows such as `supposing / suppose | Supposing / Suppose you lost your phone, what would you do?` could hit the broad pre-generation duplicate guard on the raw target string. This looked confusing and could stop grammar generation before the app had the final grammar card sentence.
2. After editing a generated card in the editor, the next safe action was not obvious. The user should not have to regenerate after manually fixing a reviewed card.

## Changed

- Grammar rows no longer use the broad raw-string duplicate precheck before AI generation.
- Grammar duplicates are checked at the correct moment: when the reviewed grammar card is written to Anki, using the exact Grammar note `Sentence` field.
- Vocabulary and grammar card editors now include a direct action:

```text
Save + add to Anki
```

- Saving an edited card keeps it in `ready` state and updates the in-memory Batch payload immediately.
- Status messages now explicitly say the edited card can be added immediately.

## Behaviour after this hotfix

- For grammar input like:

```text
supposing / suppose | Supposing / Suppose you lost your phone, what would you do?
```

Batch should generate the grammar card instead of showing a confusing raw duplicate block.

- If the generated card is edited manually, the user can either:
  - click `Save changes`, then `Add this card`, or
  - click `Save + add to Anki` directly from the editor.

No `Regenerate` is required after a manual card edit.
