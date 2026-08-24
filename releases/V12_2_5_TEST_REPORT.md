# v12.2.5 test report

- `python -m compileall -q src tests`: PASS
- `tests/ui`: 47 passed (run with a minimal CustomTkinter import stub because the clean CI environment does not install the desktop GUI dependency)
- Smart Vocabulary contract / vocabulary import prompt tests: 5 passed
- New v12.2.5 regression coverage: 8 tests for whole-source chunking, material-size messaging, Smart Vocabulary whole-document budgeting, definition-vs-example detection, mixed per-item Queue routing and mode locking.
- One pre-existing Smart Grammar prompt assertion (`Never put the rule itself in sentence`) still fails identically in untouched v12.2.4; v12.2.5 does not introduce it.
