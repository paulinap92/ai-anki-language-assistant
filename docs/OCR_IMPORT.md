# Import Material workflow

The Import Material tab prepares Batch candidates only. It never adds cards directly to Anki.

## Default free workflow

This is the main workflow for normal use. It avoids AI/API calls after text is extracted.

```text
Load TXT/HTML/PDF/image, or paste text
→ Extract text locally
→ Clean/edit the extracted text if needed
→ Look for words / phrases OR Look for sentences
→ Cherry-pick candidates on the right
→ Mark each item as word/phrase, grammar, or sentence
→ Send selected candidates to Batch / Queue
→ review generated cards
→ add to Anki
```

Local candidate search is heuristic. It does not need Gemini, Claude, OpenAI, or Mistral. It simply finds useful chunks from the extracted text so the user can decide what becomes a card.

## Local buttons

- `Look for words / phrases` finds short list-like chunks, vocabulary lines, table cells, and short phrases.
- `Look for sentences` finds full sentences/questions that can be used as examples, sentence cards, or grammar examples.
- If text is highlighted, these buttons use the selected text. If nothing is highlighted, they use all extracted text.

## Cherry-pick cards

Each candidate card can be marked as:

- `As word/phrase` → Batch mode: Vocabulary
- `As grammar` → Batch mode: Grammar
- `As sentence` → Batch mode: Provided examples

Then use `Send selected to Batch / Queue`.

## Manual candidate builder

Use this when the local search found a useful sentence but you want to pair it with a specific target.

```text
highlight word/phrase → Use selection as target
highlight example → Use selection as example
choose vocabulary / grammar / provided_example
Add candidate
```

## Optional AI assist

The `AI assist: find candidates` button is optional and uses the Card AI provider selected at the top of the app. Skip it for the free workflow.

## Mistral OCR mode

Mistral is used only for cloud text extraction from PDF/image files.

```text
Load PDF/image
→ Run Mistral OCR
→ Mistral extracts text
→ use free local Look for words/sentences buttons
→ cherry-pick
→ Send selected to Batch / Queue
```

Mistral OCR does not automatically generate candidates in the default workflow.

## Installation

Base app:

```bash
pip install -r requirements.txt
```

For local OCR on images/scanned PDFs:

```bash
pip install pillow pytesseract PyMuPDF pypdf
```

You must also install the Tesseract desktop executable and make sure it is in PATH. On Windows, install Tesseract OCR, then restart the terminal/IDE.

For Mistral OCR:

```bash
pip install mistralai
```

Add to `.env`:

```env
MISTRAL_API_KEY=your_mistral_key_here
MISTRAL_OCR_MODEL=mistral-ocr-latest
```

## Costs

- Local TXT/HTML/PDF text extraction: free.
- Local Tesseract OCR for images/scanned PDFs: free, but requires the Tesseract executable.
- Local candidate search/cherry-pick: free.
- Optional AI assist: uses the selected Card AI provider and consumes that provider's normal text-generation credits.
- Mistral OCR: cloud API call; uses Mistral credits.
- Audio is separate and still uses the Audio provider in the Speech / Audio tab.

## Safety rule

Do not use Import Material as `image → Anki`.

Always use:

```text
image/PDF/text
→ extract readable text
→ local search / manual / optional AI candidates
→ candidate preview/cherry-pick
→ Send to Batch
→ Batch review
→ Anki
```

## v9.1.8 note: Grammar Batch from sentences

In Import Material, grammar marking is intentionally sentence-first. When a candidate is marked as grammar, the app sends only the selected sentence/fragment to Batch with `batch_mode = Grammar`. Import Material does not guess the grammar focus and does not build `target | same sentence` rows. Batch is responsible for identifying the useful grammar structure during generation.
