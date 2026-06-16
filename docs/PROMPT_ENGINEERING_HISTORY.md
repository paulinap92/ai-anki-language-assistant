# Prompt Engineering History

## Vocabulary prompt v3 — word-first validation and multilingual explanations

### Observed failures

- Random contexts forced words into unrelated situations.
- The model produced grammatical but pragmatically unnatural examples.
- Misspelled or invented inputs were accepted and assigned fictional definitions.
- The model occasionally returned a different expression from the user's input.
- Polish translations could be misspelled or invented.
- Fixed-length collocation lists encouraged weak or artificial combinations.
- Translation and explanation language was hard-coded to Polish.
- The modern Conversation tab silently used `Strong B2/C1` because the level selector was missing.

### Root causes

- Context was selected before the expression was understood.
- Prompt constraints were not backed by application-level validation.
- Output schema had no validation metadata.
- UI did not expose explanation language or conversation level consistently.

### Changes

1. Removed random example contexts.
2. Added input validation fields: `is_valid`, `validation_error`, `suggested_correction`.
3. Added exact-input preservation in the prompt and provider code.
4. Added meaning-driven context and natural-collocation requirements.
5. Added translation spelling and semantic checks.
6. Allowed variable-length synonym and collocation lists.
7. Added `explanation_language`, including `No translation`.
8. Updated classic and modern vocabulary GUIs.
9. Restored the conversation answer-level selector in the modern GUI.
10. Kept the grammar feature and separate Anki grammar card type.

### Code-level guard

For valid cards, providers compare the returned expression with the original input and reject mismatches.

### Trade-off

Existing Anki field names such as `TranslationPL` remain unchanged for compatibility with existing note types. Their content can now be produced in the selected explanation language, or left empty in `No translation` mode. A future note-model migration can rename these fields safely.

### Regression cases

- `thorough` must not be forced into a sunset context.
- `pizza` must receive a food-related example because of its meaning, not random selection.
- misspelled inputs must return validation failure.
- returned valid expression must match exact input.
- `short fuse` should use established collocations only.
