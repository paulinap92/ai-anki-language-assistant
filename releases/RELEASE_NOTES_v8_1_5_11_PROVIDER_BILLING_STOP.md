# v8.1.5.11 Provider billing/error stop

Small Batch reliability hotfix after Claude returned HTTP 400 with exhausted credits.

## Fixed

- Anthropic/Claude exhausted-credit errors are now detected even when the API returns HTTP 400 instead of 402.
- Auto Batch now treats provider billing/credit problems as fatal provider errors and stops immediately instead of skipping one failed item and continuing through the queue.
- Batch preview/status now shows a friendly message: add credits or switch Card AI provider, then retry failed/rate-limited items.
- Expected provider runtime failures such as billing, quota, auth, server errors and timeouts are logged as warnings instead of full stack-trace exceptions.
- Autosave reason for these cases is now `provider error: <item>` instead of misleading `rate limit: <item>`.

## Not changed

- This does not add Anthropic credits or change billing. The user must add credits in Anthropic or switch to Gemini/OpenAI.
- OCR remains planned for v9.
