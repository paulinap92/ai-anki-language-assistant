# Anki Card Model

## Main note type

The application creates this note type automatically:

```text
AI Vocabulary Light Card
```

## Fields

| Field | Purpose |
|---|---|
| `Word` | Target word or phrase. |
| `Language` | Target language, for example English or Spanish. |
| `PartOfSpeech` | Part of speech or phrase type. |
| `TranslationPL` | Natural Polish translation. |
| `Definition` | Short target-language definition. |
| `Example` | Natural example sentence in the target language. |
| `ExamplePL` | Polish translation of the example sentence. |
| `Synonyms` | HTML chips with synonyms or close alternatives. |
| `Collocations` | HTML chips with useful phrases and usage patterns. |
| `GrammarNote` | Short grammar or usage note in Polish. |

## Template files

The HTML and CSS are stored in:

```text
src/anki/templates.py
```

This keeps presentation separate from AnkiConnect request logic.

## Field rendering

The conversion from `VocabularyCard` to Anki fields happens in:

```text
src/anki/field_builder.py
```

All AI-generated text is escaped before being inserted into Anki HTML fields.

## Duplicate behaviour

Cards are added with:

```python
"allowDuplicate": False
```

If Anki rejects a card as duplicate, `AnkiClient.add_card()` raises `ValueError`.

## Legacy migration model

Older Basic notes can be migrated to:

```text
AI Vocabulary Light Card · Migrated
```

This model has only:

- `Front`
- `Back`

Its template parses the old Basic card HTML at display time. The migration is intentionally manual inside Anki to preserve scheduling and review history.
