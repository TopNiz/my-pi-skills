# Longhorn IP template

Branded A4 documents for Longhorn IP LLC: letters, reports, memos and meeting
minutes, generated from a Markdown body plus a small metadata file.

The design uses the logo, gold (`#d9b626`) and brown (`#6a593d`) sampled from
longhornip.com, a sans-serif stack (Helvetica Neue in the PDF), brown table headers
with a gold rule, and zebra striping.

---

## Requirements

```bash
which pandoc weasyprint
# brew install pandoc weasyprint
```

Only the Python standard library is used beyond those two tools.

---

## Quick start

```bash
cd ~/.agents/skills/md2pdf/templates/longhornip

# Report
./build.py examples/report.md  --meta examples/report.json  --out /tmp/report.pdf

# Letter
./build.py examples/letter.md  --meta examples/letter.json  --out /tmp/letter.pdf

# Meeting minutes
./build.py examples/minutes.md --meta examples/minutes.json --out /tmp/minutes.pdf

# Memo, metadata entirely from flags
./build.py examples/memo.md --type memo \
  --title "Wildanger invoices of 23 June 2025" \
  --to "Nizar Ayed|Khaled Fekih-Romdhane" --from "Nicholas Peters" \
  --date "14 October 2026" --out /tmp/memo.pdf
```

If `--out` is omitted, the PDF is written next to the Markdown file, same base name.

---

## Document types

| `--type` | Structure |
|---|---|
| `report` | Brand header, title, optional subtitle, Markdown body, AI note |
| `letter` | Brand header, recipient block, date and reference line, subject, body, signature |
| `memo` | Brand header, title, To/From/Date/Reference/Subject table, body, signature |
| `minutes` | Brand header, title, meeting details table, body, signature only if requested |

The body is ordinary Markdown. Headings, paragraphs, bullet and numbered lists,
tables, blockquotes, code blocks and images all work.

---

## Metadata

Supplied as JSON with `--meta`, and/or as flags. **Flags win over the JSON file.**

```json
{
  "type": "letter",
  "title": "...",
  "subtitle": "...",
  "date": "14 October 2026",
  "ref": "LHIP-ACC-2026-015",
  "subject": "...",
  "to": ["Ms Ina Hagebaum", "Steuerberatung Blum", "Erftstrasse 102a", "41460 Neuss"],
  "from": "Nizar S. Ayed",
  "meeting": {
    "date": "14 October 2026",
    "time": "17:00 - 18:00 CET",
    "location": "Microsoft Teams",
    "chair": "Nizar Ayed",
    "attendees": ["Nizar Ayed", "Khaled Fekih-Romdhane"],
    "apologies": ["Ina Hagebaum"]
  },
  "signature": {
    "name": "Nizar S. Ayed",
    "role": "VP Engineering - Europe",
    "org": "Longhorn IP LLC",
    "contact": "www.longhornip.com<br>Mobile | +33 6 87 57 46 35"
  },
  "closing": "Kind regards,",
  "ai_note": false
}
```

Notes:

- `signature.contact` accepts HTML, which is why `<br>` works there.
- `"signature": false` removes the signature block. Minutes have none unless the
  key is present.
- `ai_note: true` appends the "AI generated document, reviewed and approved by the
  signatory" line. Off by default.
- Keys not relevant to the chosen type are ignored.

### Flags

| Flag | Effect |
|---|---|
| `--type report\|letter\|memo\|minutes` | document type |
| `--meta file.json` | metadata file |
| `--out file.pdf` | output path |
| `--html-only` | write the HTML, skip the PDF |
| `--keep-html` | keep the intermediate HTML next to the PDF |
| `--title`, `--subtitle`, `--date`, `--ref`, `--subject` | text fields |
| `--to`, `--attendees`, `--apologies` | lists, separated by `|` or newlines |
| `--from`, `--location`, `--time`, `--chair` | text fields |
| `--signature-name`, `--signature-role`, `--signature-org`, `--signature-contact` | override the signature |
| `--no-signature` | drop the signature |
| `--ai-note` | add the AI notice |

---

## Design

| Element | Rule |
|---|---|
| Page | A4, margins 16 mm sides, 19 mm bottom |
| Footer | "Longhorn IP LLC · www.longhornip.com" left, `page / total` right, suppressed on page 1 |
| Logo | `assets/logo.jpg`, 52 mm wide, above a 2.5 pt gold rule |
| h1 | 17 pt, brown `#4d412c` |
| h2 | 12.5 pt, 3 pt gold bar on the left |
| Tables | brown header, white text, gold underline, zebra `#faf7ef`, 8.8 pt |
| Body | 9.8 pt, line-height 1.5, sans-serif |

Customise by editing `style.css`. The colours are declared once at the top in
`:root`, so a brand change is a four-line edit.

---

## Tips

- **Keep a table on one page**: wrap it in `<div class="avoid-break">` inside the
  Markdown (raw HTML passes through pandoc).
- **Force a page break**: `<div class="page-break"></div>`.
- **Images**: relative paths in the Markdown are resolved against the Markdown
  file's folder and rewritten to `file://` URIs, so images work from any output
  directory.
- **Glyph safety**: U+FE0E and U+FE0F variation selectors are stripped, the same fix
  `md2pdf.sh` applies, to avoid `.LastResort` tofu boxes with arrows such as `↔`.
- **Check the output** renders as expected: open the PDF, or convert a page with
  `pdftoppm -jpeg -r 80 page.pdf p` and look at the image.
