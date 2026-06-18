# Anki Card Models

## Vocabulary note type

The application creates and maintains:

```text
AI Vocabulary Light Card
```

### Fields

| Field | Purpose |
|---|---|
| `Word` | Exact target word or phrase. |
| `Language` | Target language, for example English or Spanish. |
| `PartOfSpeech` | Part of speech or phrase type. |
| `TranslationPL` | Explanation-language translation. The legacy field name is preserved for compatibility. |
| `Definition` | Short definition in the target language. |
| `Example` | Natural example sentence in the target language. |
| `ExamplePL` | Example translation in the selected explanation language. |
| `Synonyms` | HTML chips with synonyms or close alternatives. |
| `Collocations` | HTML chips with established collocations and usage patterns. |
| `GrammarNote` | Short grammar or usage note. |

When `No translation` is selected, translation fields remain empty and the template hides the corresponding sections.

## Grammar note type

Grammar analyses use:

```text
AI Grammar Light Card
```

### Fields

| Field | Purpose |
|---|---|
| `Sentence` | Original sentence entered by the learner. |
| `Language` | Target language. |
| `Meaning` | Meaning explained in the target language. |
| `Structure` | Main grammar pattern. |
| `Breakdown` | Explanation of the sentence components. |
| `Usage` | When and why the structure is used. |
| `ContextExample` | Natural context using the same structure. |
| `Contrast` | Comparison with a related structure. |
| `CommonMistake` | Typical incorrect form and correction. |

## Template implementation

HTML and CSS are stored in:

```text
src/anki/templates.py
```

The conversion from validated domain models to Anki fields happens in:

```text
src/anki/field_builder.py
```

All model-generated text is escaped before insertion into HTML fields.

## Duplicate and update behaviour

New cards are still protected against accidental duplicates.

When an exact vocabulary expression or grammar sentence already exists, the application can update the existing note rather than creating another card.

### Exact-match fields

- vocabulary cards: `Word`;
- grammar cards: `Sentence`.

### Update flow

```text
findNotes
→ notesInfo
→ compare normalised primary field
→ ask the user
→ updateNoteFields
```

Updating the existing note preserves its note ID, scheduling, and review history.

See:

```text
docs/ANKI_UPDATE_EXISTING_CARDS.md
```

## Legacy migration model

Older Basic notes can be migrated to:

```text
AI Vocabulary Light Card · Migrated
```

This model contains:

- `Front`
- `Back`

The migration remains manual inside Anki so scheduling and review history are preserved.
