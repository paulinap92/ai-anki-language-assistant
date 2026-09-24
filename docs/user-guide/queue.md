# Queue

**Queue** is the review and batch-processing path for structured or already extracted material.

Typical inputs include vocabulary targets, grammar targets, mixed rows, and `target | example` rows.

## Workflow

```text
Prepared rows / Import Material
        ↓
Queue review
        ↓
Generation per item type
        ↓
Validation
        ↓
Final review
        ↓
Anki
```

Queue preserves the card type of imported items and supports resuming saved sessions.

!!! important "Duplicate protection"
    Queue-level checks improve UX, but the final Anki write boundary remains authoritative. A stale precheck must never be able to create a duplicate.
