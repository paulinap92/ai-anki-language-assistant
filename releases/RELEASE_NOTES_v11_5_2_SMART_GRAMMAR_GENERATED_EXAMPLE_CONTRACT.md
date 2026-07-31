# v11.5.2 — Smart Grammar generated-example contract

## Goal

Fix Smart Grammar import cases where the model correctly classifies a source fragment as a grammar rule, but still copies the rule/definition into the learner-visible `sentence` / audio field.

## Changes

- Added a dedicated Smart Grammar candidate extraction prompt for OCR/imported text.
- Added explicit `source_role`, `example_origin`, and `needs_review` candidate metadata.
- Made the Smart Grammar contract field-first:
  - `target` = grammar focus / structure / source target.
  - `sentence` = learner-visible example sentence for audio.
  - `source_rule` = original rule, definition, explanation, use note, or exercise instruction.
- For `source_role="grammar_rule"`:
  - `source_type="rule"`
  - `strategy="generated_example_from_rule"`
  - `source_rule` keeps the original textbook rule.
  - `sentence` must be a newly generated natural learner example.
  - `example_origin="generated_from_rule"`
  - `needs_review=true`
- Updated multimodal import prompt with the same Smart Grammar source-role contract.
- Updated Batch Grammar prompt so rule/definition text is never preserved as the `sentence` field.
- Updated Import Material parsing so a rule candidate is not sent to Batch as `target | rule text` unless it is explicitly marked as a generated learner example.

## Example

Source rule:

```text
El uso más común del infinitivo compuesto consiste en expresar un arrepentimiento o formular un reproche por acciones que no sucedieron o no se cumplieron en el pasado.
```

Expected candidate:

```json
{
  "type": "grammar",
  "target": "infinitivo compuesto para expresar arrepentimiento o reproche",
  "source_role": "grammar_rule",
  "source_type": "rule",
  "strategy": "generated_example_from_rule",
  "source_rule": "El uso más común del infinitivo compuesto consiste en expresar un arrepentimiento o formular un reproche por acciones que no sucedieron o no se cumplieron en el pasado.",
  "sentence": "Lamento no haber estudiado más para el examen.",
  "example_origin": "generated_from_rule",
  "needs_review": true
}
```

## Non-goals

- No language-specific phrase list was added for Spanish/English rule detection.
- No new final card type was added. Smart Grammar remains an import strategy; final Batch mode remains `Grammar`.
