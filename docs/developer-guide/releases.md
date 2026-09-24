# Releases

Use releases to keep code behavior, tests, documentation, and changelog aligned.

## Release checklist

- [ ] Confirm the intended version and scope.
- [ ] Run focused regression tests for changed high-risk paths.
- [ ] Run the full relevant test suite.
- [ ] Verify `.env.example` matches supported configuration.
- [ ] Update user-facing documentation for changed workflows/providers.
- [ ] Mark planned features as planned; do not document them as shipped.
- [ ] Update `CHANGELOG.md`.
- [ ] Run `mkdocs build --strict`.
- [ ] Launch the desktop app and smoke-test the affected workflow.
- [ ] Commit/tag only after code and documentation agree.

## Documentation preview

During development:

```powershell
mkdocs serve
```

## GitHub Pages

GitHub Pages deployment is intentionally **not configured by this initial documentation setup**.

When publishing is approved later, add a deliberate deployment workflow/process and test the built site first. Do not couple the first local MkDocs setup to an automatic public deployment.
