# Devlog Script — Fixing a Bad Vocabulary Generation Pipeline

## Hook

"My flashcard app generated a sentence about being *thorough while watching a sunset*. It was grammatical, but nobody would naturally say it. The bug was not only the model — it was my generation pipeline."

## 1. Show the failures

Display:

- an invented Polish word,
- `thorough` forced into a sunset context,
- `short fuse` inserted into a travel-app meeting,
- weak collocations,
- a misspelled input receiving a confident definition.

## 2. Explain the root cause

The old code selected a random context first. The model then had to force the expression into that context.

Show the removed `EXAMPLE_CONTEXTS` list and `random.choice(...)`.

## 3. Show the new word-first pipeline

```text
validate input
→ preserve exact expression
→ identify common meaning
→ identify natural collocations
→ choose meaning-driven context
→ generate example
→ self-check
```

## 4. Show application-level validation

Explain that prompt instructions are not enough. The provider now rejects a valid response when `word_or_phrase` differs from the user's exact input.

Invalid inputs return structured metadata instead of fictional content.

## 5. Show multilingual explanation settings

Demonstrate:

- English vocabulary with Polish explanations,
- English vocabulary with Spanish explanations,
- `No translation` mode.

Mention that both classic and modern GUIs expose the setting.

## 6. Show the Conversation bug fix

The modern GUI previously hard-coded `Strong B2/C1`. Show the restored level selector and the selected value being sent to the feedback method.

## 7. Show before and after

Use the same benchmark inputs and compare outputs. Explain that quality is measured through exact-input preservation, naturalness, translation correctness, collocation quality, and JSON validity.

## 8. Close

"This was not just rewriting a prompt. It required error analysis, schema changes, code validation, UI changes, regression cases, and documentation."
