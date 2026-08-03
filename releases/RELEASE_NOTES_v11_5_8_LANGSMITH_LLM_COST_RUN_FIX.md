# v11.5.8 — LangSmith LLM Cost Run Fix

## Goal

Make LangSmith cost tracking work for direct/custom provider calls by logging the actual model request as a dedicated child run with LangSmith-compatible LLM metadata and usage.

## What changed

- Keep the app workflow trace as a chain run, e.g. `vocabulary_card_generation`, `grammar_card_generation`, or `provided_example_card_generation`.
- Add a nested child run named `<feature>.llm` with `run_type="llm"` for the real OpenAI/Gemini/Claude provider call.
- Add LangSmith cost-identification metadata to the child LLM run:
  - `ls_provider`
  - `ls_model_name`
  - `ls_invocation_params.model`
- Return top-level `usage_metadata` from the LLM child run:
  - `input_tokens`
  - `output_tokens`
  - `total_tokens`
- Best-effort attach `usage_metadata` to the current LangSmith run tree for SDK versions that support runtime run-tree mutation.
- Keep the local app cost summary as a fallback estimate when provider token usage is missing.

## Expected LangSmith shape

```text
vocabulary_card_generation      run_type=chain
└── vocabulary_card_generation.llm  run_type=llm
    ├── metadata.ls_provider
    ├── metadata.ls_model_name
    └── output.usage_metadata
```

## Test after update

1. Enable LangSmith in `.env`.
2. Generate a new card, for example `short fuse`.
3. Open the new trace in LangSmith.
4. Check the child `.llm` run for token usage and cost.

Old traces will not be backfilled; test with new runs only.
