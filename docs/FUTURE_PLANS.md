# Future Plans / Roadmap

This document summarizes the planned direction for AI Anki Language Assistant after v10.6.1.

The current priority is not to rebuild the app from scratch. The plan is to keep the working desktop app stable and gradually add stronger UX, quality control, and LLMOps features.

---

## 1. Import Material UX — next cleanup

Current direction:

```text
Paste text / screenshot
        ↓
Reviewed source text
        ↓
Find candidates without AI / with AI
        ↓
Candidate drafts / cherry-pick
        ↓
Staged suggestions → Batch / Queue
```

Planned improvements:

- keep **Paste text / screenshot** as the main fast input path;
- improve the empty states and helper texts;
- keep **+ Add missing candidate** as a small fallback, not a main workflow;
- make OCR quality warnings less aggressive for short but valid word lists;
- add clearer handling for vocabulary lists, columns, tables, and textbook screenshots;
- preserve a smooth cherry-pick flow: edit, select, remove, then send to Batch.

Recent lesson from v10.6.1:

Short OCR text does not automatically mean bad OCR. A short list like:

```text
creepy fast-moving gripping haunting
heart-warming heavy going implausible intriguing
moving thought-provoking
```

is valid learning material and should not be blocked by a scary **Poor OCR** warning.

---

## 2. OCR Quality Gate v2

Current status:

- Good / Medium / Poor OCR quality gate exists.
- Mistral OCR works much better than local Tesseract on difficult screenshots.
- Short valid word lists are now treated more carefully.

Planned improvements:

- distinguish between:
  - short vocabulary lists,
  - natural paragraphs,
  - tables/columns,
  - noisy OCR garbage;
- show a warning only when the extracted text is genuinely unreliable;
- add suggestions such as crop image, use higher resolution, use Mistral OCR, or paste text manually;
- avoid blocking extraction when text is short but linguistically clean;
- optionally add a small **OCR confidence explanation** in the UI.

---

## 3. Suggested Expressions v2

Current target flow:

```text
AI suggestions
        ↓
checkbox + edit/remove
        ↓
Add selected to queue
        ↓
Staged for Batch / Queue
```

Planned improvements:

- keep editable suggestion drafts as the source of truth;
- make sure the queue always uses edited values;
- optionally add labels such as phrase, collocation, grammar pattern, interview phrase;
- add better filtering so weak or too obvious suggestions are not shown;
- support quick promotion of a suggestion to vocabulary or grammar card.

---

## 4. Grammar Flow Stabilization

Current rules to preserve:

- if AI finds a target plus example, the candidate should be **Grammar target**;
- **Use for Grammar** must not erase the target;
- grammar without target should become **Grammar from sentence**.

Planned improvements:

- improve visual distinction between vocabulary, sentence, grammar target, and grammar from sentence;
- add better previews before sending grammar candidates to Batch;
- keep examples and targets together through the whole flow.


---

## 4A. Grammar Exercise OCR Mode — future feature

Textbook exercise screenshots should not be treated like plain vocabulary lists.
They need a dedicated workflow because they often contain gaps, answer options,
and short sentences that should eventually become audio-ready grammar cards.

Planned workflow:

```text
OCR screenshot / pasted exercise
        ↓
Reviewed source text
        ↓
Find grammar exercises
        ↓
Exercise drafts
        ↓
user fills answer OR AI solves with review
        ↓
one completed sentence = one Grammar card = one audio sentence
        ↓
Batch / Queue
```

Planned draft fields:

- exercise type: fill gap / multiple choice / transformation;
- grammar topic, for example modals, obligation, permission, necessity;
- raw sentence with blank;
- answer options, if present;
- selected/correct answer;
- completed sentence to read aloud;
- optional short explanation or rule note.

MVP idea:

- detect lines with blanks such as `___`, `(not)`, alternatives, or numbered
  exercise rows;
- create editable exercise drafts rather than final cards;
- let the user type the answer manually;
- optional **Solve with AI** button, but always with review;
- send only completed, reviewed sentences to Batch / Queue.

Important rule:

```text
Do not add raw gap-fill exercises directly to Anki.
Convert them into completed sentence-first Grammar cards after review.
```

---

## 5. Speech / STT Diagnostics

Current status:

- v10.2 added **Play last recording** and **Open audio file**;
- recordings are saved under `.audio_cache/last_recording.wav`;
- Whisper sometimes cuts or misses part of the spoken answer.

Planned improvements:

- compare WAV recording with transcription manually during tests;
- add clearer STT status messages;
- keep the last recording easy to replay;
- later add transcription diagnostics: audio duration, detected text length, possible truncation warning.

---

## 6. Local / Free Mode

Current status:

- Ollama Local is experimental;
- Piper Local works with `C:\tools\piper`;
- Gemma is slow and can mix languages, so it should stay experimental for now.

Planned improvements:

- keep local mode optional;
- use local/free tools where they are good enough, such as TTS or simple experiments;
- do not force local models into production-quality card generation if quality is unstable;
- document recommended local setup separately from the main cloud workflow.

---

## 7. LLMOps / Observability Roadmap

This is the planned portfolio-level upgrade.

The app should not treat LLM calls as a black box. Each important model call should be measurable in terms of:

- model/provider;
- prompt version;
- input/output tokens where available;
- estimated cost;
- latency;
- validation result;
- retry count;
- user feedback: Good / Bad.

### Planned minimum implementation

No rewrite is required. The first step should be a thin observability layer around existing functions:

```text
generate_card()
validate_card()
repair_card()
batch_generate()
ocr_extract()
        ↓
trace / metrics logging
        ↓
LLMOps dashboard or LangSmith traces
```

Suggested tools:

- **LangSmith** for traces and prompt/model quality inspection;
- optionally **Langfuse** or a simple local SQLite/Postgres log for custom cost/latency dashboard.

### Why it matters

This turns the project from “an app that calls an LLM” into an app with basic LLMOps practices:

- cost awareness;
- latency monitoring;
- prompt versioning;
- quality metrics;
- validation and retry tracking;
- model comparison.

### Example metrics for future dashboard

| Metric | Example |
|---|---:|
| Total requests | 132 |
| Average cost per card | 0.003 EUR |
| Average latency | 2.4 s |
| Validation pass rate | 87% |
| Retry rate | 13% |
| Cheapest successful model | Gemini Flash / local model |
| Most expensive model | Claude / GPT |
| Best prompt version | vocab_prompt_v7 |

### Future portfolio wording

```text
Implemented LLMOps monitoring for an AI flashcard generation app, tracking token usage, estimated cost per generation, latency, prompt versions, validation pass rate and user feedback to compare models and optimize cost-quality trade-offs.
```

---

## 8. RAG / Agent Direction — later, not now

This app does not need a full LangChain/LangGraph rewrite immediately.

Later, a separate or extended project can add:

- RAG over language course materials;
- unit/topic-based retrieval;
- document ingestion pipeline;
- vector store such as Chroma or Qdrant;
- LangGraph workflow for OCR → extraction → validation → card generation;
- LangSmith tracing for the whole pipeline.

This should be treated as a later portfolio upgrade, after the current desktop app is stable.

---

## Suggested version order

| Version | Focus |
|---|---|
| v10.6.2 | Documentation roadmap and future plan cleanup |
| v10.6.8 | Grammar Batch preview labels + Exercise OCR future plan |
| v10.7 | Import Material polish + OCR quality gate v2 |
| v10.8 | Suggested Expressions v2 + better candidate labels |
| v10.9 | STT diagnostics and Whisper truncation checks |
| v11.0 | LLMOps MVP: trace/log model calls, latency, validation and feedback |
| v11.1 | Simple LLMOps dashboard or LangSmith integration notes/screenshots |
| v12.x | Optional RAG/LangGraph extension |

---

## Current product direction

The app should become:

```text
A practical AI language-learning assistant with OCR import, editable candidate selection, conversation practice, Anki export, speech support, and measurable LLM quality/cost controls.
```

The strongest portfolio angle is:

```text
AI + language learning + OCR + human-in-the-loop review + Anki automation + LLMOps quality/cost monitoring.
```
