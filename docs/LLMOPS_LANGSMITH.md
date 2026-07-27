# LLMOps / LangSmith tracing

v11.0 adds an optional LangSmith observability layer. It is meant for debugging and portfolio screenshots, not for normal Anki usage.

## What it traces

The desktop app wraps configured AI providers and records events for:

- vocabulary card generation;
- grammar card generation;
- provided-example card generation;
- Conversation Practice start and feedback;
- raw AI calls used by Import Material AI candidate extraction;
- manual test trace from the `LLMOps / LangSmith` tab.

The UI tab also keeps a local event log. This local log works even when LangSmith is disabled.

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Add this to `.env`:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=ai-anki-language-assistant
LANGSMITH_REDACT_INPUTS=true
```

Then run the app:

```bash
python main_gui_custom.py
```

Open the `LLMOps / LangSmith` tab and click `Refresh status`.

## Redaction

`LANGSMITH_REDACT_INPUTS=true` is recommended by default. With redaction ON, pasted OCR/book text and model outputs are summarized as length/word-count placeholders before being sent to LangSmith.

Use full prompts/outputs only if you are comfortable sending the source material to LangSmith:

```env
LANGSMITH_REDACT_INPUTS=false
```

## How to test

1. Open the app.
2. Go to `LLMOps / LangSmith`.
3. Click `Test trace`.
4. Check the local event log.
5. If tracing is enabled and the API key is valid, open the LangSmith project and check the run.

## Portfolio angle

This feature demonstrates that the app treats LLM calls as observable production-like operations. The next step is a Streamlit dashboard over LangSmith runs with:

- total traced calls;
- average latency;
- validation pass rate;
- retry/error rate;
- runs by provider/model;
- recent failed or low-quality generations;
- links to LangSmith traces.


## v11.3 quality metrics

The tracer now records quality and review metadata, not only raw AI calls.

Each generated-card event can include:

- `provider` and `model`;
- `feature` and `source` workflow (`single_flashcard`, `batch_queue`, `grammar_tab`, `conversation_practice`, `import_material_grammar`);
- `prompt_version`;
- `latency_ms`;
- `validation_passed`;
- `red_flags_count`;
- `issue_type` such as `invalid_input`, `exact_input_changed`, `example_target_mismatch`, `translation_issue`, `topic_mismatch`, `language_mismatch`, `missing_required_field`, `naturalness_issue`, `wrong_source_focus`, or `audio_sentence_mismatch`;
- `outcome` such as `generated`, `generated_with_warnings`, `invalid_input`, `added_to_anki`, `updated_existing_note`, `skipped`, or `add_failed`.

The app also records local human-review outcomes when a reviewed card is added to Anki, updated, skipped, or fails during export. These local events help connect generation quality with learner decisions without requiring every UI action to become an external LangSmith run.

Status wording was clarified:

- `disabled`
- `configured but inactive: package missing`
- `configured but inactive: API key missing`
- `enabled`

The `Open LangSmith app` button opens `https://smith.langchain.com/`.
