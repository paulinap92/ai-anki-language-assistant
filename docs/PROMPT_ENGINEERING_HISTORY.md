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

---

## Case — Literal interpretation of a fixed multi-word expression

### Observed failure

Input:

```text
curso de reciclaje
```

Generated meaning:

```text
a course teaching how to recycle waste correctly
```

In educational and professional usage, the established meaning is usually a refresher or updating course for professionals.

### Root cause

The prompt analysed the individual components `curso` and `reciclaje` instead of first treating the complete expression as one lexical unit.

### Prompt change

Prompt version `v4-phrase-level-meaning` now requires the model to:

- treat the complete input as one lexical unit;
- identify established meanings of compounds, idioms, and fixed phrases;
- avoid composing the meaning from literal translations of individual words;
- check educational, professional, cultural, regional, and idiomatic usage;
- keep the definition, translation, example, and collocations consistent with the selected phrase-level meaning.

### Expected output

```text
Definition: Curso destinado a actualizar o renovar conocimientos profesionales.
Translation: kurs doszkalający / szkolenie aktualizacyjne
Example: La empresa organizó un curso de reciclaje sobre los nuevos procedimientos de seguridad.
```

### Regression case

`curso de reciclaje` should be included in the vocabulary benchmark with the failure category:

```text
literal interpretation of a fixed expression
```

---

## UX improvement — Updating an existing Anki card

### Observed problem

Duplicate prevention correctly stopped a second card from being added, but users could discover an error only after the original card had already been saved. The application provided no direct way to replace the incorrect fields.

### Implemented solution

When an exact vocabulary word/phrase or grammar sentence already exists in the selected deck, the application now asks whether the user wants to replace the existing note with the reviewed version.

The update preserves the Anki note and its review history while replacing its fields through AnkiConnect `updateNoteFields`.

### Supported flows

- classic vocabulary GUI;
- modern single-card mode;
- Batch / Queue mode;
- grammar cards;
- vocabulary generated from Conversation Practice.

### Engineering rationale

Updating the existing note is preferable to deleting and recreating it because it preserves the note identity and accumulated Anki review history.


---

## Multi-provider evaluation: Claude integration

### Goal

Add Claude behind the existing provider abstraction without duplicating prompt or parsing logic.

### Engineering change

- added `ClaudeVocabularyClient`,
- reused the same prompts and Pydantic response models,
- preserved exact-input validation,
- added configuration through environment variables,
- added mock-based unit tests without real API calls.

### Evaluation value

The same benchmark inputs can now be run against Gemini, OpenAI, and Claude while keeping the prompt contract constant. This allows comparison of JSON reliability, translation accuracy, example naturalness, collocations, latency, and cost.
