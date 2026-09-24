# Changelog

## v12.4.9 — Free cloud provider options

- Added OpenRouter as a selectable LLM provider using the existing OpenAI-compatible client path; the default model is `openrouter/free` and can be overridden per card/import/review workflow.
- Added Groq Cloud STT as a third speech-to-text option next to Local Whisper and OpenAI Cloud, defaulting to `whisper-large-v3-turbo`.
- Groq STT receives the same selected language and dynamic conversation/topic/vocabulary prompt as the existing STT providers.
- Extended Setup/.env status and starter configuration for `OPENROUTER_API_KEY`, `GROQ_API_KEY` and their model settings.
- Reused the already-installed `openai` SDK for both OpenRouter and Groq compatibility endpoints, so no new runtime dependency is required.
- Added regression tests for provider construction, workflow model routing, language/context forwarding and Setup configuration.
- Added Russian and Japanese as selectable learning languages, including STT language codes and voice-library filtering; Japanese remains cloud-TTS-first when no matching local Piper voice is installed.

## v12.4.8 — Multilingual Piper + cloud STT

- Piper Voice Library language filter now expands from the live catalog instead of the original short list.
- Added explicit Piper paths for German, French, Italian and Portuguese while keeping auto-discovery for any downloaded Piper language.
- Added OpenAI Cloud STT as a Setup-selectable alternative to local Whisper.
- Added cloud-only requirements file and STT/Piper regression tests.

## v12.4.7 — Semantic source-role routing

- Fix Smart Vocabulary misclassifying headings/labels such as `A PLANNER or SPONTANEOUS` as provided learner examples.
- Add semantic `source_role` classification: `usage_example`, `heading_label`, `definition_context`, `list_item`, `fragment`, `exercise`, `unknown`.
- Allow only `usage_example` to be preserved as a Provided Example.
- Keep headings, labels, definitions, fragments and exercises as Vocabulary/context and generate a fresh learner example in Queue.
- Make Queue respect the semantic role instead of treating “contains target” as sufficient evidence that a source fragment is a valid example.
- Add regression tests for the real `planner` heading failure.

## v12.4.6 — Global duplicate guard

- Align duplicate identity with the actual card front: Vocabulary uses `Word`; target-first Grammar uses `Target`.
- Scan the whole Anki collection at the final Vocabulary/Grammar write boundary instead of relying on active-deck-only checks.
- Keep a final exact guard in the Batch fast path so a stale precheck cannot create a duplicate.
- Treat Vocabulary and Provided Example rows with the same target as one card identity.
- Deduplicate Import Material and Queue rows by final card identity rather than `target + source sentence`.
- Precheck reliable Grammar targets before provider generation.
- Add regression coverage for the real duplicate holes.

## v12.4.5 — Strict Grammar generation contract

- Rewrite only Grammar generation around one small contract: TARGET, STRUCTURE, RULE, EXAMPLE, EXPLANATION.
- Require `example_demonstrates_structure` and `target_is_structure` self-checks in the same LLM request.
- Reject a generated Grammar result when either semantic self-check is false or missing.
- Add regression tests for the real failures where a grammar description became EXAMPLE and a prose rule became TARGET.
- Keep Vocabulary, Queue, Import, Learning Profile and downstream Anki/UI models unchanged through a compatibility adapter.

## v12.4.4 — Target-first Grammar cards

- Rebuild Grammar generation around a target-first contract instead of using the example/rule sentence as the card title.
- Add a dedicated short `target` field (for example `Third conditional` or `have as a dynamic verb`) and keep `structure` as a compact formula/pattern.
- Require one real communicative example sentence; rules, definitions, headings and meta-sentences are explicitly forbidden from the example field.
- Add provider self-checks for `target_is_valid` and `example_demonstrates_target` in the same generation request.
- Use the Learning Profile explanation language for grammar meaning, usage, breakdown, contrasts and mistake explanations while keeping target-language forms/examples unchanged.
- Strengthen Smart Grammar extraction so long textbook rules are normalized to concise targets and preserved as source rules instead of becoming card titles.
- Stop source-focus repair from forcing long rule text back into the generated target.
- Redesign the Anki grammar template: concise grammar target first, then pattern, one example with audio, how it works, usage, contrasts and common mistakes.
- Remove the competing `Natural context` example from the visible card and keep the compatibility `ContextExample` field aligned to the main example.
- Existing grammar note types are upgraded in place with `Target` and `ExplanationLanguage`; old notes fall back to their existing `Structure` on the front.

## v12.4.3 — Non-blocking first-run profile startup

- Fix a Windows/PyCharm startup hang introduced by mandatory first-run Learning Profile onboarding.
- Remove the nested `wait_variable` loop that could leave a live Python process with no visible window before the application's real Tk mainloop started.
- Show Learning Profile as the first normal application screen and build the main UI only after `Save profile & continue`.
- Add startup milestones to `ai_anki_app.log`: profile required, profile window painted, profile saved, and main UI built.
- Preserve the v12.4.1 Basic local `target | example` parser and v12.4.2 deferred Anki discovery.

## v12.4.2 - Visible startup and non-blocking Anki discovery

- Paint a real startup window before loading provider configuration so Windows/PyCharm no longer looks completely idle during startup work.
- Add `logs/startup.log` (and `startup_private.log`) with milestone-level startup diagnostics and a visible startup error dialog if initialization fails.
- Make the mandatory first-run Learning Profile screen explicitly deiconify/lift itself before waiting for profile completion.
- Defer the initial AnkiConnect deck lookup until Tk has entered its event loop, so Anki being closed or slow cannot prevent the application window from appearing.
- Keep the v12.4.1 direct local `target | example` / TSV parser unchanged.

## v12.4.1 - Basic local target/example parsing

- Fix the Basic local finder so clean `target | example` and TSV rows are parsed directly without AI.
- Preserve both the target and exact example as a Provided Example candidate instead of treating the whole row as an unstructured sentence.
- Keep duplicate targets when their example sentences differ, while removing exact duplicate rows.
- Rename the local action to `Examples / sentences` and explain the accepted prepared format directly in Import Material.
- Fall back to the existing free sentence splitter only when the material does not contain structured target/example pairs.

## v12.4.0 - Mandatory Learning Profile and language-aware local audio

- Add a mandatory first-run Learning Profile gate. The main application is not shown until the user chooses a learning language, target level and explanation/feedback language.
- Persist the learner profile in local `user_profile.json` and keep provider/API setup separate in `.env` / Setup.
- Make the Learning Profile the single source of truth for Create Card, Import Material, Queue, Conversation, speech language, Voice Lab samples and feedback/explanation language.
- Remove duplicate user-facing language selectors from the top bar, Create Card, Queue, Conversation and Speech & Audio. Users edit language/level once in Profile.
- Add a dedicated Profile tab plus a compact active-profile summary and Edit action in the main header/workflows.
- Make Piper voice selection strictly language-aware. A Spanish profile no longer silently falls back to an English Piper model when no Spanish model is installed; the app directs the user to Voice Library instead. Multilingual cloud voices remain valid across languages.
- Improve Queue session recovery: add one-click `Resume latest` with date/progress/language/deck summary, keep manual JSON loading as `Load file…`, and stop old session files from silently changing the active learner profile.
- Warn when a saved Queue language differs from the active Learning Profile instead of mutating global language settings behind the user's back.

## v12.3.4 - Semantic target validation and clean Import reruns

- Move lexical morphology validation into the same AI card-generation request instead of trying to encode every language's conjugation/declension rules locally.
- Vocabulary cards now carry `target_usage` (`exact`, `valid_inflection`, `mismatch`, `uncertain`) together with the exact `used_form_in_example` surface form.
- Local validation now trusts a model-confirmed valid inflection only when the declared surface form literally occurs in the generated example. This correctly accepts cases such as Spanish `adherirse a` → `se adhiere a` without weakening synonym/mismatch checks.
- Old cards without semantic metadata keep a conservative legacy fallback, but pattern uncertainty is surfaced as review rather than pretending the local matcher understands all morphology.
- Prevent stale persisted morphology warnings from reappearing when current semantic metadata proves the target usage is valid.
- Start every deliberate Import Material AI candidate search as a fresh review state, clearing previous-language candidates, filters and pagination before rendering the new run.
- Add search generation IDs so delayed automatic retries from an older run cannot overwrite a newer candidate search after the user changes language/settings.
- Freeze language/mode/provider settings across automatic retries and add raw/parsed/merged/deduplicated candidate counts to logs for diagnosing runaway outputs such as impossible 1000+ candidate responses.

## v12.3.3 - Mixed Queue routing fix

- Fix mixed Import Material transfers so Queue shows `Mixed` whenever imported rows contain more than one preserved card type.
- Keep the Queue-wide selector stable while browsing typed imported rows instead of replacing it with the current row's Vocabulary / Grammar / Provided examples type.
- Preserve each imported row's own `batch_mode` and route generation per item.
- Recompute the correct Mixed/single imported Queue mode when resuming older Queue autosaves.

## v12.3.2 - Unified OpenAI and Gemini Voice Library

- Added **OpenAI built-in voices** to the in-app Voice Library alongside Piper and ElevenLabs. The library now exposes the current built-in OpenAI TTS voice set, including Nova, Shimmer, Marin and Cedar.
- Added all **30 Gemini TTS voices** with their provider style labels (for example Zephyr / Bright, Puck / Upbeat and Sulafat / Warm).
- OpenAI and Gemini voice previews are generated directly inside the app with the user's own configured API key and the current Voice Lab sample text; no external player is opened.
- `Use selected` now switches the active Speech & Audio provider/voice and synchronizes Conversation audio settings. Built-in cloud voices require no download step.
- Fixed runtime voice-ID resolution in Conversation so user-added ElevenLabs/Piper voices and newly selected cloud voices are sent to the provider by their real voice ID/path instead of a UI label.
- Voice Library search works for OpenAI/Gemini names and Gemini style descriptors.
- Expanded the normal OpenAI/Gemini voice dropdowns to the same complete provider voice sets, so the Voice Library and regular TTS selectors no longer disagree.
- Preview UI explains that OpenAI/Gemini preview generation may incur normal API usage.

## v12.3.1 - Smart Vocabulary example routing and review fixes

- Smart Vocabulary now automatically routes a candidate to `Provided example` when the imported source contains a complete real usage sentence that uses the target. Users no longer need to reclassify every vocabulary+example row manually before Queue.
- Glossary definitions and source context remain `Vocabulary`; definition-like text is never promoted merely because it explains the target.
- Queue therefore preserves exact Smart Vocabulary source examples as `target | sentence` and uses the Provided Example generation path automatically.
- Recalibrated Candidate Review so `Recommended` can mean either advanced + relevant language or strongly topic-central language with high learning value, without quotas. `Useful` remains the default middle tier and `Optional` remains for odd/document-specific material.
- Added visible `Select all` and `Select visible` actions to Candidate Review, alongside Recommended/Useful selection controls.
- Fixed standalone Piper on Windows to send subprocess stdin explicitly as UTF-8, preventing `UnicodeEncodeError` for emoji, Polish, Spanish and other non-cp1252 text.

## v12.3.0 - In-app Voice Library for Piper and ElevenLabs

- Added a dedicated **Voice Library** window inside Speech & Audio so users can browse, preview and add voices without leaving the app.
- Piper now loads the public `rhasspy/piper-voices` catalog on demand, filters by language/search text, plays public preview samples in-app, downloads the `.onnx` + `.onnx.json` pair, and automatically reloads TTS providers after installation.
- Added **Add local Piper .onnx** and **Open Piper folder** actions. Imported Piper voices are copied into the user voice library and discovered automatically on later starts.
- Piper TTS providers now support multiple installed voice models instead of a single fixed model path. Voice selection uses the chosen model rather than silently falling back to the first configured Piper voice.
- Added ElevenLabs **Voice Library** search and **My Voices** browsing through the user's own `ELEVENLABS_API_KEY`, including in-app preview of provider samples and adding shared voices to the user's ElevenLabs voice collection.
- User-selected ElevenLabs voice IDs are remembered in a local non-secret registry so they remain selectable after restarting the app; API keys remain only in `.env`.
- Added `PIPER_VOICE_DIR` support (default `voices/piper`) so downloaded/local voices no longer need to be individually hard-coded in `.env`.
- Voice Library network work runs in background threads so catalog searches/downloads do not freeze the Tk UI.

## v12.2.9 - Educational priorities and source safety limits

- Reworked Candidate Review priorities around learning value instead of source location. `Recommended` now requires an advanced item that is strongly relevant to the lesson/topic and remains reusable; ordinary useful vocabulary stays `Useful`; odd, document-specific, low-reusability, low-confidence and very long items stay `Optional`.
- Added explicit review metadata to Import Material AI extraction (`advancedness`, `topic_relevance`, `reusability`, `learning_value`, `document_specificity`) without changing Smart Vocabulary candidate-count semantics or imposing quotas.
- Removed the old behavior where merely appearing in a Vocabulary/Key Terms section could make nearly every candidate `Recommended`. Missing review metadata now safely falls back to `Useful` rather than `Recommended`.
- Large reviews (>25 candidates) now select only `Recommended` items by default so 70–150 candidates do not immediately flood Queue. Small reviews select `Recommended + Useful` but leave `Optional` unchecked. Added a `Select recommended + useful` action.
- Candidate cards now show the educational signals used for review ranking so users can understand why an item landed in a tier.
- Strengthened Import Material source-size protection with an explicit maximum of 8 full-source AI analysis parts in addition to word/character safeguards. Larger/book-sized sources must be analysed by selected chapter/section.
- Material-size summaries now show the full-source analysis-part safety limit while keeping candidate count entirely content-driven.

## v12.2.8 - Balanced candidate review priorities

- Fixed Candidate Review classifying nearly every Smart Vocabulary result as `Recommended`.
- `Recommended` is now deliberately conservative and reserved mainly for explicit lesson vocabulary/expression sections, highlighted items, and strong idioms.
- Generic phrases, collocations, grammar candidates, provided examples and candidates that merely have a valid source sentence now default to `Useful` instead of being promoted automatically.
- Low-confidence, review-needed, very long and obvious document-specific/named-entity candidates remain `Optional`.
- Review priority still never deletes candidates and does not affect Smart Vocabulary extraction itself.

## v12.2.7 - Import size guardrails and scalable candidate review

- Added source-size guardrails to Import Material without reintroducing a fixed candidate-count target. Small sources run normally; large sources are warned before AI analysis; very large/book-sized sources require a selected chapter/section instead of one full-source run.
- Added `Find from selected text` so users can analyse one chapter/section directly from the Source text panel.
- Material-size warnings appear immediately after TXT/HTML/PDF/OCR/paste text becomes available and show approximate words, characters and AI analysis parts.
- Kept full-source chunking for normal/confirmed large sources; nothing is silently truncated and candidate count remains content-driven.
- Reworked Candidate Review for large result sets with 25-item pagination, search, type filters and `Recommended / Useful / Optional` review priorities. Review priority organizes the list only and never deletes candidates.
- Added `Select recommended`, `Select visible`, and clearer candidate/type counts so 100+ candidates no longer appear as one unmanageable wall.
- Added shutdown diagnostics that log the exact Tk close source, Queue position and running background workflows before cleanup, plus unhandled Tk callback tracebacks. This should make the next unexpected app close diagnosable instead of leaving only `Runtime cleanup completed`.

## v12.2.6 - Content-driven Import Material candidate counts

- Removed the fixed Smart Vocabulary `~80` whole-document result target. Candidate count is now determined by the material itself.
- Removed fixed candidate quotas from Smart Vocabulary, generic Import Material, Smart Grammar and direct multimodal candidate prompts.
- A sparse source may return only a few useful candidates; a dense glossary or advanced lesson may legitimately return 100+ without being padded or cut to a target number.
- Whole-source chunk results are merged and deduplicated without a final candidate-count truncation.
- The Import Material size summary now explicitly says there is no fixed candidate count and that the result depends on the source.
- Kept only a high per-request runtime runaway guard to protect the desktop UI from malformed/extreme provider responses; this guard is not an extraction target and is not shown to the model.

## v12.2.5 - Whole-source Import Material and typed mixed Queue

- Removed the silent 24,000-character Import Material cutoff. Long source text is now split into bounded AI parts with overlap, analysed completely, merged and deduplicated.
- Added a visible material-size summary immediately after TXT/HTML/PDF/OCR/paste loading: character count, approximate word count and the number of AI analysis parts.
- Restored selective Smart Vocabulary behavior across long documents by applying one whole-document result budget after chunk merge; explicit vocabulary/expression sections are preserved first and continuous-prose candidates are kept to the mature ~80-item target.
- Fixed candidate-type normalization that could collapse Grammar / Provided Example rows when no explicit default mode was supplied.
- Replaced per-candidate `As word / Use for Grammar / As sentence` actions with a visible `Type` selector so changing a candidate to Grammar is immediately obvious.
- Import Material now sends Vocabulary, Grammar and Provided Example candidates to Queue with their own per-item type locked. The Queue-wide Input type selector no longer reclassifies imported mixed material.
- Smart Vocabulary source examples stay Vocabulary items. A valid source usage can still be preserved during generation without changing the card type to Provided Example.
- Glossary definitions that explain a target without using it (for example a definition of `cronyism`) are kept as source definition/context instead of being treated as Provided Sentences.
- Queue now shows a mixed-type summary and explains that the Input type selector applies only to clean TXT/CSV loaded directly into Queue.

## v12.2.4 - Restore original Import Material modes and Smart Vocabulary behavior

- Restored the full mature Import Material mode set: `Provided examples`, `Vocabulary`, `Vocabulary + source examples`, `Smart vocabulary`, `Grammar`, `Smart grammar import`, and `Mixed`.
- Restored the pre-v12.0.8 Smart Vocabulary extraction contract: explicit vocabulary/expression sections are complete, continuous prose mining is selective, and continuous-prose Smart Vocabulary is capped by prompt at 80 candidates rather than encouraged to scan the entire document.
- Restored the original 24,000-character AI analysis window for Import Material instead of sending up to 60,000 characters in vocabulary modes.
- Kept later UI, Conversation, audio, Queue and provider fixes from v12.2.3.

# Changelog

## v12.2.3 - Queue naming, conversation flow and readable progress

- Reworked Conversation so the user chooses the practice mode first and only sees controls relevant to that mode.
- Topic controls now disappear entirely in flashcard mode; flashcard source/deck/selection controls disappear in topic mode.
- Replaced mode-specific start labels with one clear `Start conversation` action and moved model/coaching controls into a quieter Advanced row.
- Simplified the public tab names to `Queue`, `Speech & Audio`, `Conversation`, and `Advanced`; removed remaining user-facing `Batch` / slash naming from the main UI.
- Clarified Queue as the fast path for clean structured input and renamed `mode` wording to `input type`.
- Replaced the developer-style Queue counter dump with `Prepared X of Y · N waiting`, a progress bar, and only non-zero result counters.
- Clarified Import Material: TXT/HTML are read locally with no model/API; OCR/provider controls are hidden for plain-text sources, while AI is used only at the later candidate-search step.
- Renamed text-loading actions from extraction language to `Read material locally`, `Source text`, and `Find candidates with AI`.
- Preserved v12.2.2 Smart Vocabulary behavior and v12.2.1 conversation topic/voice isolation.

## v12.2.2 - Restore Smart Vocabulary import behavior

- Restored the original `Smart vocabulary` Import Material mode as the recommended/default vocabulary workflow.
- Smart vocabulary again uses the mature smart contract: scan the whole lesson for lexical targets and preserve exact source examples only when they are genuinely useful.
- Removed the narrow `Examples / sentences` option from the Import Material dropdown; `Provided examples` remains available for clean prepared input in the Batch/Queue workflow.
- Kept a separate `Vocabulary` mode for strict lexical extraction, plus Smart Grammar routing and Auto/Mixed classification.
- Kept the v12.2.1 Conversation topic-isolation and tutor-voice fixes unchanged.

## v12.2.1 - Conversation mode isolation and tutor voice control

- Fix flashcard Conversation Practice leaking a previously entered topic into the start prompt, feedback prompt, STT context and MODE summary.
- Disable the topic field in flashcard mode and restore the previous draft when switching back to topic mode.
- Add explicit Conversation Practice tutor audio provider, voice and model selectors.
- Filter ElevenLabs presets by the selected conversation language so a generic/British voice cannot silently outrank Spanish voices.
- Make Voice Lab sample text follow the selected audio language while preserving user-edited custom preview text.
- Keep Conversation TTS playback inside the application.

# v12.2.0 — Local / Hybrid / BYOK user setup

- Added a first-run Setup tab with Fully local, Hybrid / BYOK and API / BYOK profiles.
- The GUI can now open with no configured AI provider instead of failing before startup.
- Added safe starter/import/reload `.env` workflows and an Ollama reachability/model check.
- Added profile-aware provider routing and lazy cloud SDK imports so local-only installs do not require cloud AI packages.
- Added `requirements-local.txt` and `requirements-hybrid.txt`, while keeping `requirements.txt` as the full install alias.
- Import Material now shows only locally available or configured cloud OCR methods for the selected profile.
- Updated user-facing setup/privacy documentation for early distribution.

# v12.1.1 — Import Material UX simplification

- Renamed all user-facing `Batch / Queue` wording to simply `Batch`.
- Reduced Import Material from seven implementation-oriented extraction strategies to four product-facing choices: `Vocabulary & expressions`, `Grammar`, `Examples / sentences`, and `Auto`.
- Kept the mature legacy extraction contracts internally for compatibility: Vocabulary & expressions preserves useful source context, Grammar uses smart grammar routing, Examples / sentences preserves exact source pairs, and Auto uses mixed classification.
- Added short in-UI explanations for each Import mode and made AI extraction the primary path, with the local finder presented as an optional fallback.
- Simplified candidate-review wording and Batch handoff labels.

## v12.1.0 - Workflow UI cleanup and in-app voice lab

- Merged the old Single flashcard and Grammar tabs into one `Create Card` workspace with a clear Vocabulary / Grammar selector and mode-specific preview.
- Reordered Batch so the user chooses `Vocabulary`, `Grammar`, `Mixed`, or `Provided examples` before loading clean TXT/CSV/pasted input.
- Added visible Batch guidance explaining that Batch is the fast path for already-clean structured rows, while Import Material is for lessons, HTML, PDFs, screenshots, scans and mixed/raw sources.
- Made clean CSV parsing mode-aware: Provided examples and Grammar preserve column 1 as target and column 2 as sentence instead of silently discarding the second column.
- Clarified Import Material routing: TXT/HTML are forced through local text extraction with no OCR/API call for text extraction; image/scan/PDF sources use the selected OCR/vision path before candidate extraction.
- Restored a dedicated Speech / Audio `Voice Lab` with editable sample text, Play voice, Stop and Test provider controls.
- Voice/sample previews and Fix Cards audio previews now play inside the application through the shared internal audio player instead of opening the operating-system media player.
- Added friendly Import Material provider-error handling for 429/timeouts/5xx (including OpenAI/Cloudflare 520), preserving the current source/candidates, automatically retrying up to two times, and exposing `Retry last AI extraction` instead of dumping raw provider payloads into the UI.
- Simplified crowded Batch current-card actions into two rows and renamed the observability tab to `Advanced / LLMOps`.

## v12.0.9 - Batch vocabulary duplicate target consistency

- Fixed a Batch regression where a vocabulary row containing `target | source sentence` could pass the duplicate check before generation and only be reported as duplicate after AI generation.
- Vocabulary duplicate detection now has one canonical key: the learner's target word/phrase compared with Anki's `Word` field.
- Source/example sentences are never part of the vocabulary duplicate key.
- Imported Vocabulary + source example rows prefer their stored `provided_target`; pipe/TAB rows use only the left-side target.
- The exact same original target is reused for pre-generation duplicate checks, Add-all duplicate summaries and the final Anki add/update decision.
- Sentence-only Provided Examples intentionally skip pre-generation Word lookup when no lexical target exists yet instead of comparing an entire sentence with Anki `Word`.
- Grammar keeps its separate exact `Sentence` duplicate strategy.
- Editing a Batch row clears persisted duplicate-target metadata so the edited target is checked again.

## v12.0.8 - Full-text vocabulary candidate extraction

- Fixed a regression where Vocabulary extraction could stop after explicit `Vocabulary` / `Key Terms` / `Expressions` sections and return only those list items.
- Explicit lesson vocabulary remains guaranteed and is now treated as the minimum rather than the whole result.
- After explicit lists, the AI prompt now scans the entire remaining lesson for high-value words, phrases, phrasal verbs, idioms, collocations, specialist terms and reusable C1/C2 expressions.
- Content-bearing warm-up prompts, facts, discussion questions, examples, explanations and homework can contribute vocabulary; only exercise mechanics and non-content noise are skipped.
- Removed the old instructions to keep reading-text mining minimal or artificially prefer a tiny result set.
- Increased text sent to AI for Vocabulary-family import modes from 24,000 to 60,000 characters; other import modes keep the existing 24,000-character MVP limit.
- Confirmed TXT/HTML stays a local text-extraction path: HTML tags/scripts/styles are removed locally, then the cleaned text is passed to the separate AI candidate-extraction step without OCR.

## v12.0.7 - Expanded Spanish ElevenLabs voice presets

- Added user-selected Spanish ElevenLabs presets for Andalusian voices 2-5.
- Added five Peninsular Spanish presets, including the two supplied female voices.
- Added the supplied Canarian Spanish 2 preset.
- Kept the existing Spanish, Latin American and legacy Canarian presets available.
- Voice IDs are stored exactly as supplied and remain subject to ElevenLabs account/library availability; use Preview voice to verify access.

## v12.0.6 - Conversation export and in-app audio

- Added Conversation Practice export to Markdown or plain text with session metadata, transcript, session flashcards and accumulated new-card candidates.
- Added in-app audio playback for Conversation Practice so TTS no longer opens an external media player window.
- Added manual `Read tutor reply`, `Read question` and `Stop audio` controls.
- Added optional automatic reading of the tutor reply and next question; both are enabled by default when TTS is configured.
- Generate the complete cached TTS file before playback and keep the decoded audio buffer alive until playback finishes to reduce cut-off audio.
- Stop conversation audio automatically before microphone recording starts so TTS is not captured by STT.
- Play the last STT recording in-app while keeping the recording-folder diagnostic action separate.

## v12.0.5 - Conversation feedback and STT quality

- Fixed clipped Conversation Batch buttons by stacking full-width actions.
- Added compact coaching by default with optional Detailed coaching for corrected/stronger answers and mini practice.
- Kept tutor replies conversational and brief instead of drifting into long domain lectures or overconfident specialist advice.
- Separated genuine errors, naturalness improvements and probable speech-transcription errors.
- Added context-aware faster-whisper transcription using the selected conversation language, topic, active flashcards, speaking cues and recent context.
- Enabled Whisper VAD and disabled cross-segment previous-text conditioning to reduce cutoffs and hallucinated carry-over.
- Changed the clean-install Whisper default from `base` to `small`; existing explicit `.env` choices remain unchanged.

## v12.0.4 — Conversation UX, card rotation and coverage


- Made the entire right Conversation panel vertically scrollable so staged items and session controls remain reachable on smaller windows.
- Moved speaking cues and new-card candidates above the staged queue; session flashcards are now collapsed at the bottom by default.
- Added per-turn accumulation of genuinely new flashcard candidates, capped at 0–3 new items per exchange, with clear/stage controls and disabled staging buttons when nothing new exists.
- Added persistent per-deck card selection modes: Continue rotation, Anki due cards, Random cards and Repeat last session.
- Continue rotation avoids repeating cards until the current shuffled cycle is exhausted; Reset keeps rotation progress.
- Added read-only due-card lookup through AnkiConnect without changing the active generation deck or Anki scheduling state.
- Added session coverage tracking with a live `x/30 practised` counter and used/not-used markers.
- Flashcard context now prioritizes targets not used yet and tells the tutor not to base consecutive questions on the same target unless clarification is needed.
- Added regression tests for rotation, due-card lookup and updated flashcard conversation prompts.

## v12.0.3 — Conversation suggestion separation

- Kept `Talk about a topic` suggestions unchanged.
- Split flashcard-based Conversation into three explicit concepts: session flashcards, expressions to use next, and genuinely new flashcard candidates.
- Existing deck targets are no longer offered as new cards, including case, punctuation and article-only variants.
- Longer useful collocations such as `impartir una clase magistral` remain valid even when `clase magistral` already exists.
- New-card candidates must be grounded in the current learner answer, correction, improved answer, mini-practice or tutor reply; unrelated prompt-seeded expressions are rejected.
- Added normalized duplicate filtering against the full selected Anki deck, the current session and already staged expressions.
- Added separate right-panel sections and regression tests for the new workflow.

## v12.0 — Flashcard-based Conversation

- Added a second Conversation Practice mode: `Talk based on flashcards`.
- Uses the current in-memory Batch cards without AnkiConnect.
- Generated vocabulary/grammar cards provide meanings, examples and usage; pending rows provide targets and source sentences.
- Reuses flashcard context on every feedback turn and prioritizes target expressions in suggestions.
- Limits one session to 30 usable items and skips failed/invalid/skipped Batch rows.
- Added prompt, context-building and regression tests.

## v11.5.11 — Separate Vision OCR from Image Candidate Extraction

- OpenAI/Gemini Vision OCR now transcribes image/PDF material into the reviewed text box only.
- Vision OCR no longer creates candidate drafts, Batch rows, grammar analyses or direct imports.
- Added a strict multimodal OCR prompt that preserves visible text, headings, bullets and tables while forbidding JSON/candidate generation.
- Candidate extraction remains a separate explicit `Find candidates with selected strategy` step after the user reviews/cleans OCR text.
- Direct image-to-candidate extraction is kept as an advanced compatibility helper, but it is no longer the normal OCR button path.

## v11.5.10 — UI and Import Interaction Fixes

- Screenshot/image staging is now passive; loading or pasting a screenshot no longer auto-runs OCR or multimodal import.
- Import Material text/candidate panels and Batch preview reset scroll position after repeated actions so new results are visible immediately.
- Added a Batch `Remove item` action with debounced autosave for faster repeated deletes.
- Status messages now distinguish loaded/staged sources from explicit OCR/API calls.

## v11.5.9 — Workflow-specific model selection

- Added workflow-specific model roles for card generation, Import/OCR extraction, multimodal import, and review/fix workflows.
- Import Material text candidate extraction now uses the configured import model instead of always using the normal card-generation model.
- Multimodal import now passes the configured multimodal model explicitly.
- LangSmith traces include `workflow_model_role` to make model/cost comparison clearer.


## v11.5 — Multimodal Import Extraction

- Added OpenAI/Gemini multimodal import methods for screenshot/book-photo/table extraction.
- Added table-aware candidate extraction mapping Expression → target, Example → sentence/audio, Use → source note.
- Added highlighted/marked item extraction rules for physical-book workflows.
- Added `OPENAI_MULTIMODAL_MODEL` and `GEMINI_MULTIMODAL_MODEL` env options.

# Changelog

## v12.0.2 — Conversation meaning and continuity

- Added a dedicated target-language `tutor_reply` before the next question.
- Direct learner questions and unknown flashcards are now answered before the conversation moves on.
- Conversation feedback receives recent turn history instead of treating every answer as an isolated exchange.
- Generic Anki `Front`/`Back` notes preserve `Back` as authoritative card content instead of mislabelling it as an example sentence.
- Flashcard explanations must use the card meaning, definition, back, example or usage and avoid confident invention.
- Added regression tests for Basic cards, explain-on-demand behaviour and history-aware prompts.

## v12.0.1 — Conversation deck source selector

- Flashcard conversation now defaults to a selected Anki deck.
- Added visible Flashcard source and Deck selectors inside Conversation Practice.
- Added Refresh decks and Current Batch as an optional secondary source.
- Reads vocabulary, grammar, and recognizable legacy notes without changing the card-generation deck.

This file keeps version history out of the main README. Detailed notes live in `releases/`.

## Current project line

### v11.5.12 — Audio Metadata Fields

Stored hidden TTS provider/model/voice/source metadata on Anki notes for new audio generation, Fix Cards audio repair and existing-card audio backfill.

### v11.3.3 — LLMOps Audio, Import and Review Traces

Expanded LangSmith/LLMOps observability beyond core model calls: import, smart grammar import, Batch, review outcomes, Anki outcomes, audio alignment, TTS, audio cache and audio export traces.

### v11.3 — LangSmith Quality Metrics

Added quality metadata such as validation status, red-flag count, issue type, outcome, feature/source and prompt-version metadata.

### v11.2 — Smart Grammar Import / Mixed Source Mode

Added AI classification of grammar OCR fragments and routing strategies for structure + sentence, rule-only material, transformations, exercises and sentence-only input.

### v11.1 — Grammar OCR / Source Focus Fix

Protected grammar source focus: structure stays as grammar focus, source sentence stays as sentence/audio, and rules stay as notes.

## OCR / Import and candidate flow

### v10.6.8 — Grammar Batch Preview + Exercise OCR Roadmap

Improved pending Grammar Batch preview and saved the future Grammar Exercise OCR Mode roadmap.

### v10.6.7 — Grammar sentence split + audio-ready import

Made grammar import sentence-first again so each real source sentence can become its own audio-ready grammar card.

### v10.5 — Import UX + Suggestions Queue Fix

Cleaned Import Material and Conversation suggested-expression flows so reviewed candidates go through Batch instead of direct Anki writes.

### v10.3 — Candidate Flow Trial

Added editable candidate drafts, cherry-pick flow and safer Batch item editing.

## OCR and STT milestones

### v9.1.9 — Conversation STT trial

Added a small local Whisper/faster-whisper speech-to-text trial for Conversation Practice.

### v9.1 — OCR manual picker + Mistral auto candidates

Added explicit local OCR manual picker and Mistral OCR auto-candidate workflows.

## Batch, audio and validation stabilization

### v8.1.5.x — Validation, language-neutral defaults and audio scope fixes

Stabilized Batch validation, warning overrides, language-neutral schemas/defaults, audio deck/language scope and warning single-source-of-truth behavior.

### v8.1.4 — Prompt quality and validation

Added prompt-quality validation, provider self-check fields and local card quality warnings.

### v8.1.3.x — Fix Cards and audio repair hotfixes

Improved Fix Cards visibility, audio repair and existing-note update behavior.

### v8.0 — Batch Controls and Quality Stabilization

Added Pause/Stop controls, draft review, Batch card editor, better quota handling and audio resume improvements.

## Earlier stabilization

### v7.4 — No Autocall, Rate-Limit Stop, Audio Resume

Prevented silent Batch provider calls, stopped Auto Batch on rate limits and improved audio resume behavior.

For complete historical detail, see the individual files in `releases/`.
