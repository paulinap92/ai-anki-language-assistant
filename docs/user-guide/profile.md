# Profile

The **Learning Profile** is the single source of truth for learner-facing language settings.

It stores:

- learning language,
- target level,
- support language used for explanations and feedback.

The profile is saved locally in `user_profile.json`. Provider/API configuration stays separate in `.env`.

!!! important
    Workflows should read language settings from the Learning Profile instead of maintaining independent language selectors that can drift out of sync.

Changing the profile can affect Create Card, Import Material, Queue, Conversation, speech language, and feedback/explanation language.
