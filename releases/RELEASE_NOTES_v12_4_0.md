# v12.4.0 — Mandatory Learning Profile and language-aware local audio

This release centralizes learner settings and removes repeated language selection across workflows.

## First-run profile

The app now requires a local Learning Profile before the main interface opens. The profile stores:

- learning language;
- target level / answer level;
- explanation and feedback language.

Provider/API configuration remains separate in Setup.

## One language source of truth

Create Card, Import Material, Queue, Conversation, local speech language, Voice Lab samples and voice filtering now follow the active Learning Profile. Language selectors were removed from individual workflows.

## Piper by language

Installed Piper models are filtered by the active learning language. If no matching local voice exists, the app tells the user to add one from Voice Library instead of silently falling back to a model from another language.

## Queue resume

Queue now offers `Resume latest` with a summary of the newest autosave. `Load file…` remains available for manual recovery. Loading a saved Queue no longer silently changes the active Learning Profile; a language mismatch is shown explicitly.
