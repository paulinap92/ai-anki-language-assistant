# v12.4.7 — Semantic source-role routing

This release fixes Smart Vocabulary source-example routing without adding a new regex filter.

## Real regression

Source fragment:

`A PLANNER or SPONTANEOUS`

Correct behavior:
- target: `planner`
- source role: `heading_label`
- candidate type: `vocabulary`
- Queue strategy: generate a fresh example from the target
- the heading is never used as the learner example/audio sentence

## Contract

The extraction model now classifies the visible fragment as one of:

- `usage_example`
- `heading_label`
- `definition_context`
- `list_item`
- `fragment`
- `exercise`
- `unknown`

Only `usage_example` is eligible for automatic Provided Example routing.

## Validation

- 39 focused routing/import/dedup tests pass.
- 54 UI import/vocabulary/duplicate tests pass.
