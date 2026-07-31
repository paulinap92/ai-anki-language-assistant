# v11.5.3 — Batch Raw Response UI Cleanup

## Purpose
Keep Batch completion and error UI readable during demos and real use.

## Changes
- Hide raw provider JSON and large debug payloads from the main Batch status/preview area.
- Keep raw details in autosave/logs instead of rendering them as user-facing text.
- Shorten Batch status messages and failed-item details.
- Replace visible autosave file paths with a short `Autosaved.` status.
- Preserve summary counts: total, added, updated, duplicates, invalid/blocked, failed, rate-limited, remaining.

## Why
One failed Batch item could previously dump a full raw model/provider response into the visible UI and break the layout.
