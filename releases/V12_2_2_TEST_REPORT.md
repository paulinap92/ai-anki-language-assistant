# v12.2.2 test report

## Focused regression checks

- `tests/ui/test_v12_1_1_import_ux.py`
- `tests/ui/test_v12_2_2_smart_vocabulary_restore.py`
- `tests/ai/test_vocabulary_import_prompt.py`

Result: **11 passed**.

## Wider related checks

Vocabulary/import/HTML/Batch duplicate checks pass. The existing Smart Grammar prompt-string assertion still fails exactly the same way in untouched v12.2.1; this release does not modify Smart Grammar prompt logic.

## Syntax

`python -m compileall -q src tests` passed before packaging.
