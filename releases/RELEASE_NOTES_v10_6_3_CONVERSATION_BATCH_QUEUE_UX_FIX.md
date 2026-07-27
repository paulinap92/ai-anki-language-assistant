# v10.6.3 Conversation Batch / Queue UX Fix

This hotfix removes the confusing direct-Anki action from Conversation Practice.

## Changed

- Conversation Practice no longer shows **Generate selected + add to Anki**.
- AI suggestions are now staged first, then sent to the central **Batch / Queue** workflow.
- The action is now explicit: **Add staged to Batch / Queue**.
- The panel text now makes it clear that nothing is written to Anki from Conversation Practice.
- The staged list is larger and labelled **Staged for Batch / Queue**.
- After sending items to Batch / Queue, the app shows:
  - how many expressions were transferred,
  - which Anki deck will be used later,
  - which Card AI provider is selected for generation,
  - a short item preview,
  - a confirmation that nothing has been added to Anki yet.
- A `QUEUE LOG` entry is appended to the conversation transcript.
- The app switches to **Batch / Queue** after transfer so the user can review/generate/add from one central place.

## Rationale

Conversation Practice should only collect useful expressions from feedback. Actual card generation, review, duplicate checks, and final Anki writes should happen in **Batch / Queue**, where the user can see and control the process.
