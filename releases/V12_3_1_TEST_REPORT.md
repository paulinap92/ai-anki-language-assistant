# v12.3.1 Test Report

## Focused regression tests

- Smart Vocabulary real source usage → Provided example
- Smart Vocabulary definition → Vocabulary context
- Smart Vocabulary definition naming the target → remains Vocabulary
- Smart Vocabulary → Queue end-to-end preservation of target + exact source sentence
- Candidate Review priority recalibration
- Piper executable UTF-8 stdin
- Existing Import Material mixed Queue regression coverage
- Existing v12.2.9 priority/limit coverage

Focused set: **25 passed**.

## Broader available suite

With optional Claude/Gemini SDK tests excluded because those SDKs are unavailable in the build environment: **175 passed, 2 skipped, 2 failed**.

The same two failures reproduce on the untouched v12.3.0 package and are unrelated to v12.3.1:

1. legacy Batch Grammar prompt wording assertion,
2. existing Spanish `derrumbar(se)` validator regression.

`python -m compileall -q src tests`: **passed**.
