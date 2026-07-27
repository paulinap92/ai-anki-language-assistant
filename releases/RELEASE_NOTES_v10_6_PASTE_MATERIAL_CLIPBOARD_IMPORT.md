# v10.6 Paste Material / Clipboard Import

## Goal

Make Import Material accept the fastest real-world input path:

```text
paste text or screenshot
→ Reviewed source text
→ Find candidates
→ Candidate drafts / cherry-pick
→ Batch / Queue
```

This version keeps the existing v10.5 candidate flow intact and only improves the material input step.

## Changes

### Import Material

- Added a new **Paste text / screenshot** button in the Import Material sidebar.
- Added a small **Paste or import material** dialog with:
  - **Paste text from clipboard**
  - **Paste screenshot from clipboard**
  - **Open image/PDF/TXT**
  - **Clear**
  - **Use this material**
- Plain text from the dialog is written directly into **Reviewed source text**.
- Clipboard screenshots are saved to `.import_cache/clipboard_screenshot_YYYYMMDD_HHMMSS.png`.
- Staged screenshots/files are passed through the currently selected extraction method:
  - **Local extraction (free)**, or
  - **Mistral OCR (cloud text only)**.
- After text is pasted, the app shows the existing OCR quality label: **Good / Medium / Poor**.

## Notes

- Clipboard screenshot support uses Pillow `ImageGrab.grabclipboard()`.
- This should work best on Windows. Other platforms may depend on clipboard backend behavior.
- The rest of the flow is unchanged: the user still reviews text first, then creates candidate drafts, edits/removes them, and sends selected drafts to Batch / Queue.

## Validation

- `python -m py_compile src/ui/modern_gui.py` passes.
- `python -m compileall -q src` passes.
