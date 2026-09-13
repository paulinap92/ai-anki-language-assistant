# v12.4.1 — Basic local target/example parsing

The Basic local finder now treats the app's clean `target | example` format as a first-class local import format. No AI call is used.

Example:

```text
pick up | I think things pick up then.
lined up | Have you got anything lined up or any interviews?
```

Selecting **Examples / sentences** creates two Provided Example candidates with the target and exact sentence preserved. Plain prose still falls back to the existing sentence splitter.
