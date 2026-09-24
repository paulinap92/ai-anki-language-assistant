# Grammar

Grammar cards use a **target-first contract**. The card target must be a concise grammar structure, not a textbook paragraph or a random example sentence.

The generation contract requires:

```text
TARGET
STRUCTURE
RULE
EXAMPLE
EXPLANATION
```

The same model response must also confirm that:

- the example demonstrates the structure,
- the target is a real concise grammar structure.

If either semantic self-check is missing or false, the result is rejected.

!!! danger "Project invariant"
    Do not weaken the Grammar contract to make malformed provider responses pass. Fix the provider/prompt/adapter and add a regression test for the real failure.
