# v12.1.1 Test Report

## Passed

- `python -m compileall` for source and launchers.
- 19 focused regression tests passed covering:
  - v12.1 Batch CSV mode behavior,
  - v12.1.1 four-mode Import Material UX mapping/help,
  - full-text vocabulary extraction prompt,
  - HTML local text import,
  - Batch duplicate-target handling.
- Static UX checks confirm `Batch / Queue` is no longer present in the main UI source and Import Material exposes only the four product-facing modes.

## Environment-limited full suite

Full pytest collection cannot complete in this sandbox because optional provider SDKs are not installed:

- `anthropic`
- `google.genai`

This is an environment dependency limitation, not a failure in the v12.1.1 UX changes.

## Existing unrelated targeted test

The older Smart Grammar prompt suite contains an assertion for an exact historical wording (`Never put the rule itself in sentence`) that is not present in the current prompt. This behavior predates v12.1.1 and was not changed as part of this UI simplification.
