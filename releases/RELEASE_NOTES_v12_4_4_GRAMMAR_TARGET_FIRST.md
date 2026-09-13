# v12.4.4 — Target-first Grammar cards

## Why

Real grammar cards had drifted into a sentence-first mapping where a textbook rule or explanation could become the giant card title, and the `Example` could itself be another explanation instead of an actual usage sentence. Examples observed during testing included a full rule about dynamic `have` as the title and a meta-description of the third conditional as the example.

## New grammar contract

Every generated grammar card now has distinct responsibilities:

- `target`: short learner-facing grammar identity, e.g. `Third conditional`, `have as a dynamic verb`, `used to + infinitive`.
- `structure`: compact pattern/formula.
- `sentence`: one concrete natural sentence that demonstrates the target and is used for audio.
- `meaning`: short learner explanation in the profile explanation language.
- `breakdown` / `usage` / `contrasts` / `common_mistakes`: concise learner guidance.

The same model call performs two explicit self-checks before returning JSON:

- `target_is_valid`
- `example_demonstrates_target`

No second validation API call is added.

## Card layout

The Anki grammar card is now target-first:

1. grammar target
2. short meaning/function
3. pattern
4. one real example + audio
5. how it works
6. when to use it
7. contrasts
8. common mistakes

`ContextExample` remains only for backwards compatibility and is aligned to the main `Sentence`; it is no longer rendered as a competing second example.

## Smart Grammar import

Long textbook rules are source context, not card titles. The extraction prompt now explicitly normalizes rule-like targets, for example:

`have with this meaning is a dynamic (action) verb and can be used in continuous tenses`

becomes a concise target such as:

`have as a dynamic verb`

while the original rule remains source context for final generation.

## Compatibility

Existing `AI Grammar Light Card` note types are upgraded in place by adding `Target` and `ExplanationLanguage`. Existing notes with no `Target` continue rendering by falling back to their `Structure`. Duplicate identity remains based on the example `Sentence`, so multiple examples for the same grammar structure are still possible.
