# v12.0.9 Test Report

## Scope
Batch vocabulary duplicate-target consistency for plain vocabulary and target + source-sentence rows.

## Regression cases
- `echo chamber | Social media can create an echo chamber.` resolves to duplicate key `echo chamber`.
- Stored `provided_target` wins over the rendered Batch row and generated card wording.
- Pipe and TAB target + sentence rows compare only the left-side vocabulary target.
- Plain multi-word vocabulary phrases remain intact.
- Sentence-only Provided Examples do not compare a whole sentence against Anki `Word` before generation.
- Grammar remains on its existing Sentence-based duplicate path.
- A mocked pre-generation check finds an existing `echo chamber` note and skips the provider call path.

## Automated checks
- `24 passed` across the new Batch duplicate regression suite, vocabulary import prompt tests and existing-note map tests.
- `python -m compileall -q src tests` passed.

## Existing unrelated failure
A broader quality-validator run still contains the pre-existing `derrumbar(se)` synonym/example assertion failure. The same test fails unchanged on the v12.0.8 clean package, so it is not introduced by v12.0.9.
