# v12.3.1 — Smart Vocabulary example routing and review fixes

This release fixes the Import Material workflow found during real Smart Vocabulary testing.

## Smart Vocabulary → Queue

A Smart Vocabulary candidate with a genuine exact source usage sentence is now automatically treated as a **Provided example**. The user does not need to click every candidate and change its type manually.

Example:

- target: `bounce back`
- source sentence: `She bounced back quickly after the setback.`
- Queue type: `Provided examples`
- Queue payload: `bounce back | She bounced back quickly after the setback.`

Definitions remain vocabulary context. For example, a glossary definition of `cronyism` is not treated as a learner example unless it is a genuine usage sentence.

## Candidate Review

- Added **Select all**.
- Added **Select visible** for the current filtered/page view.
- Recommended ranking is less brittle: advanced relevant language and strongly topic-central high-value language can both be Recommended without any fixed percentage/quota.

## Piper Unicode

Standalone `piper.exe` stdin is now explicitly UTF-8 on Windows, fixing crashes such as `UnicodeEncodeError: cp1252` for emoji and multilingual preview text.
