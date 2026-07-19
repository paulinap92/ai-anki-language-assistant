# v8.1.5.2 — Language-neutral schema/defaults

This release removes hidden Polish assumptions from vocabulary and conversation generation before OCR/STT work continues.

## Changed

- Added visible Batch controls for:
  - Target language
  - Explanation language
- Added visible Conversation Practice control for:
  - Feedback language
- Updated vocabulary prompt version to `v8-language-neutral-schema`.
- Updated provider JSON schema from legacy Polish-specific names:
  - `translation_pl`
  - `example_pl`

  to neutral names:
  - `translation`
  - `example_translation`
- Updated `VocabularyCard` to use neutral canonical fields while still accepting old `translation_pl` / `example_pl` autosaves.
- Updated `ConversationFeedback` to use neutral `feedback` while still accepting old `feedback_pl` responses.
- Updated Anki model fields to include neutral `Translation` and `ExampleTranslation`, while keeping `TranslationPL` and `ExamplePL` for backward compatibility.
- Updated Conversation prompt so feedback is generated in the selected feedback language, not implicitly Polish.
- Added support for `Same as target` in explanation/feedback language selectors.

## Compatibility

- Old autosaves with `translation_pl` / `example_pl` still load.
- Old provider responses with `translation_pl` / `example_pl` still parse.
- Existing Anki cards/templates using `TranslationPL` / `ExamplePL` remain supported.

## Not changed

- OCR is still deferred.
- STT is still deferred.
- Piper/Ollama are still deferred until after STT.
