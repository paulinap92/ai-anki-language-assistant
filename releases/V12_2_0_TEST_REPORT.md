# v12.2.0 Test Report

## Validation completed

- `python -m compileall -q src main.py main_gui.py main_gui_custom.py main_gui_custom_private.py` — PASS
- 49 selected regression tests — PASS
  - new Local / Hybrid / BYOK setup helpers and profile routing;
  - first-run configuration behavior;
  - Anki deck/note helpers;
  - Conversation export/audio/selection/suggestion logic;
  - HTML local text import;
  - speech cache/service/STT context/voice presets.

## New v12.2.0 regression coverage

11 dedicated setup/profile tests cover:

- profile-name normalization;
- starter `.env` creation without overwriting an existing user secret;
- safe `.env` import with backup and supported-key filtering;
- configured/missing status without exposing secret values;
- first-run `get_settings()` with no AI provider;
- local profile routing to Ollama while ignoring cloud keys;
- API profile not activating Ollama;
- local dependency file excluding cloud AI SDKs;
- hybrid dependency file including local + cloud provider dependencies;
- presence of the Setup workflow in the modern UI source.

## Existing unrelated test debt

A broader prompt/validator subset still contains the same 3 failures already present in the v12.1.1 clean base:

1. one historical Batch Grammar prompt wording assertion;
2. the existing `derrumbar(se)` vocabulary-validator assertion;
3. one historical Smart Grammar exact wording assertion.

The same three assertions were reproduced against the untouched v12.1.1 base, so they were not introduced by v12.2.0.

## Environment limitation

The container used for packaging does not have `customtkinter`, so the actual Windows GUI could not be visually launched here. `modern_gui.py` passes Python compilation, and the UI-facing additions are covered by static/regression checks. Real Windows first-run Setup, `.env` import/reload, Ollama reachability and dropdown refresh should be smoke-tested on the target machine before public release.
