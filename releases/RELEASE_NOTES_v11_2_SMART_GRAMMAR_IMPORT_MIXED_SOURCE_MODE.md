# v11.2 — Smart Grammar Import / Mixed Source Mode

## Purpose

This release improves OCR / Import Material for grammar-heavy textbook material. Instead of treating every imported grammar fragment the same way, the app now asks AI to classify the source fragment first and then choose an appropriate card strategy.

## Main rule

Different OCR grammar sources need different handling:

| Source material | Strategy |
|---|---|
| structure + example sentence | preserve the structure as target and the source sentence as audio/example |
| rule / explanation only | generate a natural example sentence, keep the rule as a source note |
| word-form transformation | preserve the transformation as target and generate/preserve an example using the transformed form |
| gap-fill / multiple-choice exercise | create an exercise draft for review instead of silently making a final card |
| sentence only | keep the sentence and infer the grammar later |

## UI changes

- Added **Smart grammar import** to Import Material AI extraction modes.
- Candidate drafts can now show:
  - `Detected as: ...`
  - `Strategy: ...`
  - `Why: ...`
  - `Rule/source note: ...`
- Batch preview now shows **SMART IMPORT ROUTING** for grammar rows.
- Mixed OCR imports preserve per-item Batch mode, so one queue can contain vocabulary, grammar and provided-example rows without the current combobox overwriting pending item modes.

## Prompt changes

The OCR candidate extraction prompt now asks AI to return optional metadata:

```json
{
  "source_type": "structure_sentence | rule | transformation | exercise | sentence_only",
  "strategy": "preserve_source_sentence | generated_example_from_rule | word_form_example | exercise_draft_review_answer | infer_later",
  "source_rule": "short original rule/exercise text when relevant"
}
```

For rule-only material, AI should generate a short natural example sentence for the future audio/example field and keep the original textbook rule as metadata, never as the audio sentence.

## Example

Input rule:

```text
We use have to to express obligation imposed by others.
```

Candidate draft:

```text
Target: have to + infinitive
Example/audio: I have to wear a uniform at work.
Detected as: rule
Strategy: generated example from rule
Rule/source note: We use have to to express obligation imposed by others.
```

## Tests

Passed:

```bash
python -m py_compile src/ai/prompts.py src/ui/modern_gui.py
python -m compileall -q src
python -m pytest -q tests/ai/test_smart_grammar_import_prompt.py tests/ai/test_batch_grammar_prompt.py
```
