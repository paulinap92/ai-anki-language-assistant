# v12.4.2 — Visible startup and non-blocking Anki discovery

This maintenance release fixes a silent-start experience on Windows/PyCharm.

## Changes

- The application now creates and paints a startup window before provider initialization.
- Startup milestones are written to `logs/startup.log` for deterministic diagnosis of silent launches.
- First-run Learning Profile onboarding is explicitly raised and painted before its modal wait.
- Initial Anki deck discovery is scheduled after the Tk event loop starts rather than blocking first paint.
- v12.4.1 local `target | example` parsing remains intact.
