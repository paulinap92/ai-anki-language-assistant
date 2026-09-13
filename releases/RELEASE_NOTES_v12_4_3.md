# v12.4.3 — Non-blocking first-run profile startup

This release fixes the silent Windows/PyCharm startup hang seen after mandatory Learning Profile onboarding was introduced.

The profile screen is now a normal first page of the application. Tk enters its real main loop immediately; no nested `wait_variable` loop runs during object construction. Saving the profile then builds the main workspace and schedules Anki discovery in the background.

Diagnostic milestones are written to `logs/ai_anki_app.log` so startup can be located precisely if another issue appears.
