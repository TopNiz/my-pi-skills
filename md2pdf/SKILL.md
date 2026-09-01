---
name: md2pdf
description: Convert Markdown documents to styled PDFs using pandoc + weasyprint with a clean A4 report layout (red headers, zebra tables, page numbers). Automatically fixes the pandoc 3.9 variation-selector bug (U+FE0E after ↔) that renders missing glyphs (.LastResort) in the PDF. Use whenever the user asks to turn a .md file into a .pdf report or document.
allowed-tools: read write edit bash
compatibility: opencode
---

# 🧾 md2pdf — Markdown → styled PDF

Convert any Markdown file into a polished A4 PDF with a single command, using **pandoc + weasyprint** and a bundled default style (red `#d81e00` headers, zebra-striped tables, page numbers bottom-center). The style is yours to replace — see [Own the style](#-own-the-style).

---

## Prerequisites

Check that the tools are installed before converting:

```bash
which pandoc weasyprint perl
```

If `pandoc` or `weasyprint` is missing, install via Homebrew and stop:

```bash
brew install pandoc
brew install weasyprint
```

The style uses fonts available on macOS: Arial Unicode MS, Apple Color Emoji, Helvetica Neue, Menlo.

## Usage

```bash
SKILL_DIR="$HOME/.agents/skills/md2pdf"

# 1. PDF next to the .md (same base name)
"$SKILL_DIR/md2pdf.sh" /path/to/document.md

# 2. Explicit output path
"$SKILL_DIR/md2pdf.sh" /path/to/document.md /path/to/output.pdf

# 3. Custom CSS instead of the default style
"$SKILL_DIR/md2pdf.sh" /path/to/document.md /path/to/output.pdf /path/to/custom.css
```

The script resolves its own directory, so it also works via a symlink or `PATH` entry:

```bash
ln -s "$HOME/.agents/skills/md2pdf/md2pdf.sh" /usr/local/bin/md2pdf
md2pdf document.md
```

## What it does

1. `pandoc` converts the Markdown to an HTML fragment.
2. A perl pass strips **variation selectors** `U+FE0E` / `U+FE0F` — pandoc 3.9 appends U+FE0E after certain arrows (e.g. `↔`), and Pango/weasyprint cannot shape that sequence with Arial Unicode MS, producing `.LastResort` fallback glyphs (tofu boxes) in the PDF. **Do not remove this step.**
3. The HTML is wrapped with the CSS (`style.css` in the same folder, or a custom one) and converted to PDF with `weasyprint`.

## 🎨 Own the style

The bundled `style.css` is just a default (a Chain-IT red theme). Since this skill is meant to be cloned and reused, make the output yours by replacing it:

```bash
# Option 1 — replace the default permanently (your own layout)
cp /path/to/your-style.css "$HOME/.agents/skills/md2pdf/style.css"

# Option 2 — per-document custom style, no file touched
"$HOME/.agents/skills/md2pdf/md2pdf.sh" doc.md out.pdf /path/to/your-style.css
```

Any valid CSS for print (`@page`, fonts, tables, headers…) works. Keep at least one `@page` rule and a readable font stack so the PDF stays A4 and clean.

## Layout of the bundled default style

- A4, margins 1.8 cm / 1.6 cm, page numbers bottom-center (`n / N`).
- Title in Chain-IT red `#d81e00`; section headers with red bottom border.
- Tables: red header row, zebra striping, full width.
- Fonts: Arial Unicode MS + Apple Color Emoji (emoji fallback), code in Menlo.

## Verifying the output

After generation, check that no glyph fell back to `.LastResort` (missing unicode characters). Requires PyMuPDF:

```bash
python3 -c "
import fitz
d = fitz.open('output.pdf')
bad = [ (p+1, s['font'], c) for p in range(len(d)) for b in d[p].get_text('dict')['blocks']
        for l in b.get('lines', []) for s in l['spans'] if '.LastResort' in s['font'] for c in s['text']]
print('LastResort glyphs:', bad if bad else 'NONE ✓')
"
```

If `.LastResort` appears, the source contains a character not covered by the font stack — replace it or extend the CSS `font-family` fallback list.

## Notes

- Works with pandoc ≥ 3.9 (the variation-selector behavior) and older versions too.
- The script is `set -euo pipefail`: any failure stops before writing a broken PDF.
- Temporary files are cleaned up automatically (`trap`).
