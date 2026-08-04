# v12.0 test report

## Passed

- `python -m compileall -q src tests main_gui_custom.py main_gui_custom_private.py`
- 9 targeted tests for:
  - topic-mode prompt compatibility;
  - flashcard start prompt;
  - flashcard feedback prompt;
  - generated vocabulary-card context;
  - pending `Provided examples` parsing;
  - failed-item filtering and 30-item limit;
  - LangSmith wrapper compatibility with flashcard context.
- Real Batch autosave smoke check:
  - 137 stored Batch items detected;
  - 137 usable unique items;
  - 30 selected for one conversation session;
  - first parsed target: `dar cuenta de`.

## Environment limitations

The container used for verification does not have the optional GUI/provider packages `customtkinter`, `anthropic`, and `google-genai`, so the Windows GUI and provider SDK test modules could not be launched here. Python syntax compilation passed for all modified source files and launchers.

## Existing unrelated failures

Three pre-existing tests fail in the uploaded v11.5.12 archive before the v12.0 changes and still fail afterward:

- one Batch grammar prompt wording assertion;
- one Spanish reflexive-verb validator assertion;
- one Smart Grammar prompt wording assertion.

They are not caused by Flashcard-based Conversation.
