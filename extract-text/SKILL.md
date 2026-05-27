---
name: extract-text
description: Extract text, OCR images/PDFs, and convert documents using the protected Apache Tika service at tika.codimeo.com. Use for PDFs, scans, screenshots, images, office documents, HTML, and other files when the user wants machine-readable text content.
---

# Extract Text

Extract text content from images, PDFs, scans, office documents, HTML, and many other file types using the protected Apache Tika service.

The helper script calls Apache Tika Server over HTTPS and writes one extracted-content file per input file.

## Setup

Credentials are stored locally in a git-ignored `.env` file in this skill directory:

```bash
cd ~/.agents/skills/extract-text
cp .env.example .env
chmod 600 .env
$EDITOR .env
```

Required variables:

```bash
TIKA_URL=https://tika.codimeo.com
TIKA_USER=tika
TIKA_PASSWORD=...
```

Do not commit `.env`. The repository `.gitignore` ignores `.env` files.

## Usage

```bash
# Extract plain text from one or more files
./extract-text.sh document.pdf scan.png screenshot.jpg report.docx

# Write outputs to a specific directory
./extract-text.sh --output-dir ./text-output document.pdf scan.png

# Print extracted content to stdout instead of writing files
./extract-text.sh --stdout document.pdf

# Extract Markdown instead of plain text
./extract-text.sh --format markdown document.pdf

# Extract HTML or JSON
./extract-text.sh --format html document.pdf
./extract-text.sh --format json document.pdf
```

## Output files

By default, outputs are written next to each input file:

- `file.txt` for `--format text`
- `file.md` for `--format markdown`
- `file.html` for `--format html`
- `file.json` for `--format json`

If an output file would overwrite the input path, the script uses `file_extracted.<ext>` instead.

## Supported inputs

Apache Tika supports many formats, including:

- PDFs, including scanned PDFs when OCR is enabled server-side
- PNG/JPEG/TIFF/GIF/WebP images when OCR is enabled server-side
- DOCX/XLSX/PPTX and other office documents
- HTML/XML
- Plain text, CSV, JSON, and many archive/document formats

## Service details

- Base URL: `https://tika.codimeo.com`
- Authentication: HTTP Basic Auth via `.env`
- Main endpoint: `PUT /tika`
- Markdown endpoint: `PUT /tika/md`
