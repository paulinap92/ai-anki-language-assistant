# Testing

The project uses `pytest`.

Run the full test suite from the repository root:

```powershell
pytest
```

For a focused change, run the relevant existing tests together with the new regression test before running the wider suite.

## Regression-test rule

A regression test should reproduce a real bug as directly as possible.

Good regression tests answer:

1. What exact input/state caused the bug?
2. Which guard, contract, or routing decision failed?
3. What behavior must now remain protected?
4. Does the test fail on the buggy implementation and pass after the fix?

Do not replace a real regression case with an unrelated synthetic example just because it is easier to test.

## High-risk areas

Changes in these areas deserve focused regression coverage:

- global duplicate identity and final Anki write guards,
- Grammar contract parsing and semantic self-checks,
- Import Material semantic source roles,
- Import Material → Queue routing,
- Learning Profile language propagation,
- provider availability/factory logic,
- STT/TTS provider selection,
- resume/autosave behavior.

## Example

The v12.4.6 duplicate regression tests verify that a duplicate found elsewhere in the Anki collection is blocked before `addNote`, and that Grammar duplicate identity uses the grammar target rather than merely the example sentence.

## Documentation checks

Before a documentation release, also run:

```powershell
mkdocs build --strict
```

This catches broken navigation/configuration issues that a plain Markdown preview can miss.
