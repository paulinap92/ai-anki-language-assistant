# Devlog Script — From Bad LLM Outputs to a Reliable Flashcard Workflow

## Hook

> My flashcard app generated a sentence about being *thorough while watching a sunset*. It was grammatical, but nobody would naturally say it. The problem was not only the model — it was my generation pipeline.

## 1. Show Version 1

Use Git:

```bash
git switch --detach v0.1.0
```

Display the original vocabulary and conversation workflow.

Explain that the application worked technically but had weak content-quality control.

## 2. Display real failures

Examples:

- invented Polish translation;
- `thorough` forced into a sunset context;
- `short fuse` inserted into an unrelated travel-app meeting;
- invalid input receiving a confident definition;
- weak collocations.

## 3. Explain the random-context root cause

Show:

```python
random.choice(EXAMPLE_CONTEXTS)
```

Explain the old order:

```text
random context
→ force word into context
→ unnatural example
```

Then display the new order:

```text
validate input
→ preserve exact expression
→ identify meaning
→ identify collocations
→ choose natural context
→ generate example
→ self-check
```

## 4. Switch to the prompt-engineering milestone

```bash
git switch --detach v0.2.0
```

Show:

- word-first prompt;
- exact-input preservation;
- invalid-input metadata;
- explanation-language selection;
- `No translation`;
- sentence-first Grammar.

## 5. Display phrase-level semantic failure

Input:

```text
curso de reciclaje
```

Bad output:

```text
a course about recycling waste
```

Correct interpretation in the educational/professional context:

```text
refresher course / professional updating course
```

Explain the fix:

```text
Treat the complete expression as one lexical unit.
Do not compose meaning from isolated words.
```

## 6. Display the Anki correction workflow

Explain the real user problem:

> I noticed the semantic error only after the card was already saved.

Display the new flow:

```text
duplicate detected
→ Replace it with this reviewed version?
→ updateNoteFields
→ preserve review history
```

## 7. Display Batch / Queue

Switch to the corresponding milestone tag.

Show:

- TXT/CSV import;
- one-card-at-a-time review;
- Add, Skip, Regenerate, and Edit;
- automatic advance;
- progress counters;
- persistent status instead of `OK` popups.

## 8. Display Practice and Print Test

Show:

- selecting cards from Anki;
- local multiple-choice checking;
- no LLM call for ordinary checks;
- printable test HTML;
- separate answer-key HTML.

## 9. Display Claude integration

Switch to the Claude milestone.

Explain that Gemini, OpenAI, and Claude now use the same prompt contract and validated models.

Mention that provider comparisons can use the same regression benchmark.

## 10. Close

> This was not just rewriting a prompt. It required error analysis, schema changes, application-level validation, UI changes, Anki update logic, regression cases, and documentation.

## Next engineering step

- restore automated test coverage;
- run provider benchmarks;
- document real trials;
- add TTS for example sentences only after current flows are protected by tests.
