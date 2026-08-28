# v12.2.8 test report

Focus: Candidate Review priority regression where nearly all imported Smart Vocabulary candidates appeared as Recommended.

Expected behavior:
- explicit lesson vocabulary / highlighted items -> Recommended
- generic reading-text phrases and collocations -> Useful
- low-confidence, review-needed, very long or obvious document-specific names -> Optional
- source sentence presence alone must not promote an item to Recommended

Validation commands are recorded in the release preparation output.
