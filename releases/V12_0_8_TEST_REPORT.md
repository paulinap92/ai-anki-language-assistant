# v12.0.8 test report

## Targeted regression tests
- `tests/ai/test_vocabulary_import_prompt.py`: verifies explicit lists are a minimum, full-document scanning is required, discussion questions remain valid vocabulary sources, and the old minimal-prose instructions are gone.
- `tests/ocr/test_html_text_import.py`: verifies HTML is read locally, visible text is preserved, markup is removed, and script/style content is not passed through.

Result: 32 targeted/regression tests passed across vocabulary import, HTML import, Conversation, Anki deck reading, STT context and ElevenLabs voice presets.

## Compile check
`python -m compileall -q src tests` passed.

## Existing unrelated test
`tests/ai/test_smart_grammar_import_prompt.py` already fails in the untouched v12.0.7 clean package because it expects the literal phrase `Never put the rule itself in sentence`, which the current Smart Grammar prompt no longer contains. This v12.0.8 vocabulary change does not modify Smart Grammar behavior.
