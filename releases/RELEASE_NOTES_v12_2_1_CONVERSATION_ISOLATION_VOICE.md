# v12.2.1 — Conversation mode isolation + tutor voice control

This hotfix addresses two regressions found during real Conversation Practice testing.

## Flashcard mode isolation

A topic entered in `Talk about a topic` could survive a switch to `Talk based on flashcards` and steer the tutor away from the selected Anki targets. Flashcard mode now ignores topic state at every layer: GUI state, start request, feedback request, STT prompt, export metadata and prompt construction.

## Tutor voice control

Conversation Practice now exposes its own Tutor audio provider / Voice / Model controls. The voice list follows the selected conversation language. ElevenLabs language-specific voices are preferred instead of a generic default voice.

## Voice Lab

The test sentence follows the selected Speech / Audio language. A user-edited sample is preserved instead of being overwritten. Playback remains in-app.

## Stronger flashcard grounding

The flashcard prompt now explicitly requires the first question to be grounded in 1–2 selected targets and subsequent questions to prefer unused targets, instead of opening with a generic unrelated topic.
