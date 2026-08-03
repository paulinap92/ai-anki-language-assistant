# v11.5.10 — UI and Import Interaction Fixes

This release fixes the annoying UI/interaction bugs that were making repeated Import, Batch, Audio-style review flows feel broken.

## Fixed

- Loading/pasting a screenshot no longer auto-runs OCR or multimodal import.
- Screenshot/image/PDF staging is now passive: the app shows the loaded source and waits for an explicit import button click.
- Import Material text and candidate panels reset scroll position after new results are rendered.
- Batch preview resets to the top whenever a new current item/result is shown.
- Added a `Remove item` action in Batch review for deleting the current row directly.
- Batch item removal uses debounced autosave so repeated deletes do not write the autosave JSON on every click.
- Import statuses now say clearly when a source is only loaded/staged and no OCR/API call has started.

## Expected flow

```text
Load image / paste screenshot
→ preview/status only
→ choose OCR/import method
→ click Extract text / Run Mistral OCR / Run multimodal import
→ review text or candidate drafts
→ send selected drafts to Batch
```

No OCR, provider call, or candidate extraction should start just because a screenshot was loaded.
