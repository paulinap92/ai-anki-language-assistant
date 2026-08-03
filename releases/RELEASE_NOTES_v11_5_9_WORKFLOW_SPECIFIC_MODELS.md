# v11.5.9 — Workflow-specific model selection

## Why

The app now separates cheap/high-volume card generation from more demanding import and review workflows.
This prevents one model choice from being used for everything: Batch card generation, OCR/import extraction,
multimodal table/photo extraction, and repair/review can use different models.

## Added

- `OPENAI_MODEL` for normal card generation / Batch.
- `OPENAI_IMPORT_MODEL` for Import Material text extraction, Smart Vocabulary, and Smart Grammar.
- `OPENAI_MULTIMODAL_MODEL` for screenshots, tables, and book photos.
- `OPENAI_REVIEW_MODEL` for review/repair/conversation feedback style workflows.
- `OPENAI_PREMIUM_MODEL` as a manual placeholder for premium experiments.
- Equivalent workflow roles for Gemini: `GEMINI_MODEL`, `GEMINI_IMPORT_MODEL`, `GEMINI_MULTIMODAL_MODEL`, `GEMINI_REVIEW_MODEL`.
- Equivalent workflow roles for Claude: `CLAUDE_MODEL`, `CLAUDE_IMPORT_MODEL`, `CLAUDE_REVIEW_MODEL`, `CLAUDE_PREMIUM_MODEL`.

## Behavior

- Single cards and normal Batch use the default card model.
- Import Material AI candidate extraction uses the import model when the provider supports workflow-specific models.
- Multimodal import explicitly uses the multimodal model.
- Import-derived grammar generation can use the import model when the item context indicates OCR/import/source-rule workflow.
- Conversation feedback / review-like calls use the review model.
- LangSmith traces include `workflow_model_role`, so model/cost comparison is easier.

## Suggested setup

```env
OPENAI_MODEL=gpt-5.6-luna
OPENAI_IMPORT_MODEL=gpt-5.6-terra
OPENAI_MULTIMODAL_MODEL=gpt-5.6-terra
OPENAI_REVIEW_MODEL=gpt-5.6-terra
OPENAI_PREMIUM_MODEL=gpt-5.6-sol
```

Gemini can be configured similarly:

```env
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_IMPORT_MODEL=gemini-2.5-flash
GEMINI_MULTIMODAL_MODEL=gemini-2.5-flash
GEMINI_REVIEW_MODEL=gemini-2.5-flash
```

## Notes

- The visible provider selector still chooses the provider.
- Model role selection is read from `.env`.
- If a workflow-specific model is empty, the app falls back to the default provider model.
