# v12.2.7 — Import size guardrails and scalable candidate review

## Import source guardrails

Candidate count is still determined by the material. The new limits apply only to **source size** so a user cannot accidentally send an entire book through dozens of model calls.

- Normal source: analyse normally.
- Large source: warn immediately after text/OCR is ready and ask for confirmation before full-source AI search.
- Very large source: block one full-source candidate search and ask the user to highlight a chapter/section and use **Find from selected text**.

No source is silently truncated. Normal and confirmed large sources continue to use chunked whole-source analysis.

## Candidate review

Large candidate sets are no longer rendered as one giant list. Review now supports:

- 25 candidates per page;
- Recommended / Useful / Optional review priority;
- Vocabulary / Grammar / Provided example filters;
- text search;
- Select recommended;
- Select visible;
- selected/priority/type counters.

The priority is an automatic review aid based on existing import metadata and obvious review-risk signals. It does **not** delete candidates and it does not change Smart Vocabulary extraction semantics.

## Shutdown diagnostics

The app now logs a shutdown request before runtime cleanup, including:

- Tk close source (`wm_delete_window`);
- current Queue index and Queue size;
- whether auto-generation or Add all was running.

Unhandled Tk callback exceptions are also logged with a traceback. This is intended to diagnose the previously observed unexplained close during long Queue generation.
