# v8.1.5.9 — Validation override + lesson/context mode

Hotfix after Batch validation became too strict.

## Changed

- Vocabulary prompt moved to `v10-lesson-context-validation`.
- Default validation stance is now lesson/context mode:
  - useful context-specific phrases, collocations, verb-object patterns, and sentence fragments are valid learning items;
  - phrases are not rejected just because they are not fixed idioms or dictionary headwords;
  - examples such as `shell rebel positions`, `raise concerns`, `submit an application`, and `take legal action` should be treated as useful context phrases.
- `invalid` should now be reserved for real garbage/OCR noise, wrong-language text, malformed wording, or items that cannot be naturally explained.
- Provider self-checks for bad collocation/translation naturalness are now SOFT warnings rather than automatic hard blockers.
- The local example-usage validator now recognizes common irregular verb anchors, including phrasal verbs such as:
  - `blow up` → `blew up`, `blown up`
  - `come across` → `came across`
  - `take over` → `took over`, `taken over`

## UI

- Added `Approve warning` in Batch current-card actions.
- A generated card with hard quality warnings can be manually approved and marked ready.
- Manual approval is saved in autosave/logs with:
  - `quality_override`
  - `quality_override_reason`
  - `overridden_quality_warnings`
- `Add all ready` no longer re-blocks cards with a saved `quality_override`.
- `Add this card` now lets the user approve a hard warning in the confirmation dialog instead of forcing edit/regenerate.

## Still strict

Hard warnings remain for clear structural problems such as:

- Cyrillic characters in fields that should be Polish/Latin script,
- empty required fields,
- changed input phrase,
- local validation showing that the example really does not use the target item.
