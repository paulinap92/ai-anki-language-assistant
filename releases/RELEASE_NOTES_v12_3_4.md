# v12.3.4 — Semantic target validation and clean Import reruns

## Card validation

The card-generation request now performs the language-aware morphology decision itself. It returns:

- `example_uses_target`
- `target_usage`: `exact`, `valid_inflection`, `mismatch`, or `uncertain`
- `used_form_in_example`: the exact surface form copied from the example

The local validator does **not** try to implement every language's conjugation system. It checks that the AI-declared surface form really exists in the example and keeps deterministic schema/quality safeguards.

Example now accepted correctly:

- target: `adherirse a`
- example: `Este microorganismo se adhiere a la ropa.`
- used form: `se adhiere a`
- target usage: `valid_inflection`

## Import Material reruns

A new candidate search now starts from a clean candidate-review state. Previous-language results are not left visible after a blocked or failed rerun. Automatic retries carry a generation ID and cannot overwrite a newer user-started search.

Logs now include per-run candidate counts at raw provider JSON, parsed part, merged, and deduplicated stages to make runaway extraction bugs diagnosable.
