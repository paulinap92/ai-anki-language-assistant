# v12.2.6 Test Report

## Automated checks

- `python -m compileall -q src tests` — PASS
- Import/Queue/Conversation/Speech/Core/Anki focused regression suite — **107 passed**

Covered changes include:

- Smart Vocabulary has no fixed 60/80/100 candidate quota.
- Generic Import Material candidate extraction has no fixed quota.
- Smart Grammar candidate extraction has no fixed quota.
- Direct multimodal candidate extraction has no fixed quota.
- Whole-document chunk merge deduplicates without truncating to 80.
- Long-source UI summary states that the full source is analysed and candidate count depends on content.
- Typed Queue and whole-source import regressions from v12.2.5 remain covered.
