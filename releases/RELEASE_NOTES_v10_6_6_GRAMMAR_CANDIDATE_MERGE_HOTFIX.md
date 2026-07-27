# v10.6.6 — Grammar candidate merge hotfix

## Why

AI candidate extraction could create two visible drafts for the same grammar point:

1. `Grammar target` from the rule/explanation text, e.g. `should have / ought to have + past participle`.
2. `Provided example` from the matching example sentence, e.g. `We should have / ought to have driven`.

This looked like duplicated or confusing output in Import Material.

## Changed

- Added post-processing for OCR/import candidates.
- When a `provided_example` clearly matches an existing `grammar` target, the app now merges them into one grammar candidate.
- The explicit grammar target is preserved.
- The real example sentence is attached to the grammar candidate.
- Rule explanation text such as `We can use ... to talk about ...` is no longer preferred over a real example sentence when a matching example exists.

## Example

Before:

```text
Grammar target
Target: should have / ought to have + past participle
Example: We can use should have or ought to have + past participle to talk about past events...

Provided example
Target: We should have / ought to have driven
Example: We should have / ought to have driven – it would have been quicker.
```

After:

```text
Grammar target
Target: should have / ought to have + past participle
Example: We should have / ought to have driven – it would have been quicker.
```

## Validation

- `python -m py_compile src/ui/modern_gui.py`
- `python -m compileall -q src`
