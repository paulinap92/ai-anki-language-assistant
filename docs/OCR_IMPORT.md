# Import Material workflow

The Import Material tab prepares Batch candidates only. It never adds cards directly to Anki.

## Two OCR workflows

### 1. Local extraction + manual picker

Use this when you want low cost and control.

Flow:

```text
Load TXT/HTML/PDF/image
→ Extract text locally
→ correct OCR text manually
→ highlight target word/phrase
→ Save selected target
→ highlight example sentence
→ Add target + example
→ Send candidates to Batch
→ review cards
→ add to Anki
```

Manual picker buttons:

- `Save selected target` stores the highlighted word/phrase as the target.
- `Add target + example` uses the saved target and highlighted sentence to create a provided-example row.
- `Add selected vocab` adds the highlighted text as a vocabulary candidate.
- `Add selected grammar` adds the highlighted text as a grammar candidate. If a target is saved, the highlighted text becomes the example sentence.

Readable candidate row format:

```text
provided example | target | sentence
provided example | sentence
vocabulary | target
grammar | structure | optional sentence
```

The old TSV format is still accepted internally.

This mode is best for screenshots, textbook vocabulary tables, grammar banks, and cases where automatic extraction selects the wrong words.

### 2. Mistral OCR auto candidates

Use this when the layout is difficult or you want a faster cloud OCR pass.

Flow:

```text
Load PDF/image
→ Run Mistral extraction
→ Mistral extracts markdown text
→ current Card AI provider extracts candidate rows
→ review/edit candidates
→ Send candidates to Batch
```

Mistral extraction is OCR only in this app. Candidate extraction still uses the selected Card AI provider such as OpenAI/Gemini/Claude.

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

- Local Tesseract OCR: no API cost, runs locally, but quality depends on the image and installed OCR language data.
- Mistral OCR: paid cloud API. It sends files to Mistral and consumes Mistral credits.
- Candidate extraction after OCR: uses your selected Card AI provider and consumes its normal text-generation credits.
- Audio is separate and still uses the Audio provider in the Speech / Audio tab.

## Safety rule

Do not use Import Material as `image → Anki`.

Always use:

```text
image/PDF
→ OCR/manual or auto candidates
→ candidate preview/edit
→ Send to Batch
→ Batch review
→ Anki
```
