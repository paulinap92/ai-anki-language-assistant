# v9.1.5 Batch sanity fix

Fixes after Batch testing:

- Removed duplicated `QUALITY WARNINGS` rendering in Batch card preview.
- Fixed false hard warning for English irregular forms like `oversleep` -> `overslept`.
- Adjusted Batch issue summary so safe duplicates/skipped duplicates are visible instead of showing a confusing "No issues" popup while the header still counts duplicates.
- Kept safe duplicates separate from true problems: problem navigation still focuses on blocked/failed/invalid/rate-limited/uncertain items.

Validation:

- `python -m compileall src` passes.
