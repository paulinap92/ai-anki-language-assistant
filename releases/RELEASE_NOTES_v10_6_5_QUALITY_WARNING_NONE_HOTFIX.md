# v10.6.5 Quality Warning None Hotfix

Small stability hotfix after v10.6.4.

## Fixed

- Fixed a Tkinter callback crash in `_approve_current_quality_warning` when a batch item had no `quality_warnings` list yet.
- `quality_warnings=None` is now treated as an empty warning list before checking stale hard warnings.

## Validation

- `python -m py_compile src/ui/modern_gui.py`
- `python -m compileall -q src`
