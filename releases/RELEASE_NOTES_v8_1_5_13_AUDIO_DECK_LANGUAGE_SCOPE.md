# v8.1.5.13 — Speech / Audio deck and language scope fix

Small UI/workflow hotfix after the v8.1.5.7 audio-tab scope cleanup.

## Fixed

- `Speech / Audio` no longer depends on the hidden global card-generation top bar.
- Added explicit local selectors at the top of `Speech / Audio`:
  - `Anki deck to scan`
  - `Card language`
- `Speech / Audio` keeps `Card AI provider` hidden, because text card generation provider is irrelevant to audio backfill.
- Audio deck selection now uses a dedicated `self._speech_deck_var` instead of silently relying on the global `self._deck_var`.
- Audio language selection now uses a dedicated `self._speech_language_var` as fallback when an Anki note has no language field.
- TTS voice presets, provider diagnostics and voice preview use the audio-tab language when the active tab is `Speech / Audio`.
- Missing-audio scan now calls `_set_speech_selected_deck()` so it scans the deck selected inside `Speech / Audio`.

## Intended UI

In `Speech / Audio`, the visible controls should now be:

```text
Anki deck to scan | Refresh decks | Card language
Audio provider    | Model         | Voice
```

The global top bar remains hidden in this tab, but the deck/language controls needed by audio are visible locally.
