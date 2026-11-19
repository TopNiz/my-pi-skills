#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Longhorn IP document builder: Markdown body + metadata -> branded HTML -> A4 PDF.

Pipeline:  pandoc (MD -> HTML fragment)  ->  branded wrapper + style.css  ->  weasyprint

Supported document types (--type):
    report    title block, optional subtitle/date/reference, body, signature
    letter    recipient block, date/reference, subject line, body, signature
    memo      To/From/Date/Subject header table, body, signature
    minutes   meeting details table (date, time, place, chair, attendees, apologies)

Usage
    build.py body.md --type report --title "Q3 status" --out q3.pdf
    build.py body.md --type letter --meta letter.json
    build.py body.md --type minutes --meta minutes.json --out minutes.pdf
    build.py body.md --type report --html-only          # HTML only, no PDF

Metadata can come from a JSON file (--meta) and/or CLI flags. CLI flags win.

JSON shape (all keys optional, unknown keys ignored):
{
  "type": "letter",
  "title": "...", "subtitle": "...", "date": "14 October 2026",
  "ref": "PR 75/24", "subject": "...",
  "to": ["Ms Ina Hagebaum", "Steuerberatung Blum", "Erftstrasse 102a", "41460 Neuss"],
  "from": "Nizar S. Ayed",
  "meeting": {
     "date": "14 October 2026", "time": "10:00-11:00", "location": "Teams",
     "chair": "Nizar Ayed",
     "attendees": ["A", "B"], "apologies": ["C"]
  },
  "signature": {"name": "...", "role": "...", "org": "...", "contact": "..."},
  "ai_note": false
}

Notes
- Relative image paths in the Markdown are resolved against the Markdown file's folder.
- U+FE0E / U+FE0F variation selectors are stripped, same fix as md2pdf.sh (pandoc 3.9
  appends U+FE0E after arrows such as ↔ and pango renders .LastResort tofu otherwise).
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
STYLE = HERE / "style.css"
LOGO = HERE / "assets" / "logo.jpg"

DEFAULT_SIGNATURE = {
    "name": "Nizar S. Ayed",
    "role": "VP Engineering - Europe",
    "org": "Longhorn IP LLC",
    "contact": "www.longhornip.com<br>Mobile | +33 6 87 57 46 35",
}

TYPES = ("report", "letter", "memo", "minutes")


# --------------------------------------------------------------------- utils
def die(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(code)


def require_tools() -> None:
    missing = [t for t in ("pandoc", "weasyprint") if shutil.which(t) is None]
    if missing:
        die(
            "missing tool(s): "
            + ", ".join(missing)
            + "\n  install with: brew install " + " ".join(missing)
        )


def strip_variation_selectors(text: str) -> str:
    return text.replace("\ufe0e", "").replace("\ufe0f", "")


def absolutise_images(fragment: str, base_dir: Path) -> str:
    """Make relative <img src> absolute so weasyprint can find them from anywhere."""

    def repl(m: re.Match) -> str:
        quote, src = m.group(1), m.group(2)
        if re.match(r"^(https?:|data:|file:|/)", src):
            return m.group(0)
        candidate = (base_dir / src).resolve()
        if candidate.exists():
            return f"src={quote}{candidate.as_uri()}{quote}"
        return m.group(0)

    return re.sub(r'src=(["\'])(.+?)\1', repl, fragment)


def md_to_html(md_path: Path) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "body.html"
        proc = subprocess.run(
            ["pandoc", str(md_path), "-f", "markdown", "-t", "html5", "-o", str(out)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            die(f"pandoc failed:\n{proc.stderr.strip()}")
        fragment = out.read_text(encoding="utf-8")
    return strip_variation_selectors(fragment)


def meta_row(label: str, value_html: str) -> str:
    return f'<tr><td class="label">{html.escape(label)}</td><td>{value_html}</td></tr>'


def lines(value) -> list[str]:
    """Accept a string with newlines, a list, or None."""
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [ln.strip() for ln in str(value).splitlines() if ln.strip()]


# ------------------------------------------------------------------ sections
def brand_block() -> str:
    logo_src = LOGO.as_uri() if LOGO.exists() else ""
    img = f'<img src="{logo_src}" alt="Longhorn IP">' if logo_src else ""
    return (
        '<div class="brand">'
        f"{img}"
        '<div class="tagline">Patent monetisation and licensing</div>'
        "</div>"
    )


def title_block(meta: dict) -> str:
    out = []
    if meta.get("title"):
        out.append(f'<h1>{html.escape(meta["title"])}</h1>')
    if meta.get("subtitle"):
        out.append(f'<div class="subtitle">{html.escape(meta["subtitle"])}</div>')
    return "".join(out)


def letter_prelude(meta: dict) -> str:
    out = []
    recipient = lines(meta.get("to"))
    if recipient:
        out.append(
            '<div class="recipient">'
            + "<br>".join(html.escape(x) for x in recipient)
            + "</div>"
        )
    meta_bits = []
    if meta.get("date"):
        meta_bits.append(html.escape(meta["date"]))
    if meta.get("ref"):
        meta_bits.append("Reference: " + html.escape(meta["ref"]))
    if meta_bits:
        out.append('<div class="letter-meta">' + " &nbsp;·&nbsp; ".join(meta_bits) + "</div>")
    if meta.get("subject"):
        out.append(f'<div class="subject">{html.escape(meta["subject"])}</div>')
    return "".join(out)


def memo_prelude(meta: dict) -> str:
    rows = []
    if meta.get("to"):
        rows.append(meta_row("To", "<br>".join(html.escape(x) for x in lines(meta["to"]))))
    if meta.get("from"):
        rows.append(meta_row("From", html.escape(meta["from"])))
    if meta.get("date"):
        rows.append(meta_row("Date", html.escape(meta["date"])))
    if meta.get("ref"):
        rows.append(meta_row("Reference", html.escape(meta["ref"])))
    if meta.get("subject"):
        rows.append(meta_row("Subject", html.escape(meta["subject"])))
    if not rows:
        return ""
    return '<table class="meta">' + "".join(rows) + "</table>"


def minutes_prelude(meta: dict) -> str:
    meeting = meta.get("meeting") or {}
    rows = []
    for label, key in (
        ("Date", "date"),
        ("Time", "time"),
        ("Place", "location"),
        ("Chair", "chair"),
    ):
        value = meeting.get(key) or meta.get(key.lower() if key != "location" else "location")
        if value:
            rows.append(meta_row(label, html.escape(str(value))))
    attendees = lines(meeting.get("attendees") or meta.get("attendees"))
    if attendees:
        rows.append(meta_row("Attendees", "<br>".join(html.escape(a) for a in attendees)))
    apologies = lines(meeting.get("apologies") or meta.get("apologies"))
    if apologies:
        rows.append(meta_row("Apologies", "<br>".join(html.escape(a) for a in apologies)))
    if meta.get("ref"):
        rows.append(meta_row("Reference", html.escape(meta["ref"])))
    if not rows:
        return ""
    return '<table class="meta meeting-meta">' + "".join(rows) + "</table>"


def signature_block(meta: dict) -> str:
    if meta.get("signature") is False:
        return ""
    sig = dict(DEFAULT_SIGNATURE)
    sig.update(meta.get("signature") or {})
    closing = meta.get("closing") or "Kind regards,"
    contact = sig.get("contact") or ""
    parts = [
        '<div class="signature">',
        f'<div class="closing">{html.escape(closing)}</div>',
        f'<div class="name">{html.escape(sig["name"])}</div>',
    ]
    if sig.get("role"):
        parts.append(f'<div class="role">{html.escape(sig["role"])}</div>')
    if sig.get("org"):
        parts.append(f'<div class="org">{html.escape(sig["org"])}</div>')
    if contact:
        parts.append(f'<div class="contact">{contact}</div>')
    parts.append("</div>")
    return "".join(parts)


def ai_note_block(meta: dict) -> str:
    if not meta.get("ai_note"):
        return ""
    return (
        '<div class="ai-note">&#129302; AI generated document, reviewed and approved '
        "by the signatory &#10024;</div>"
    )


# --------------------------------------------------------------------- build
def compose(meta: dict, body_fragment: str) -> str:
    doc_type = meta.get("type", "report")
    css = STYLE.read_text(encoding="utf-8")

    prelude = []
    if doc_type in ("report", "minutes"):
        prelude.append(title_block(meta))
    if doc_type == "letter":
        prelude.append(letter_prelude(meta))
    elif doc_type == "memo":
        prelude.append(title_block(meta))
        prelude.append(memo_prelude(meta))
    elif doc_type == "minutes":
        prelude.append(minutes_prelude(meta))

    tail = []
    if doc_type in ("letter", "memo"):
        tail.append(signature_block(meta))
    elif doc_type == "minutes" and meta.get("signature") not in (None, False):
        # Minutes carry a signature only when the metadata asks for one.
        tail.append(signature_block(meta))
    tail.append(ai_note_block(meta))

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        f"<title>{html.escape(meta.get('title') or meta.get('subject') or 'Longhorn IP document')}</title>\n"
        f"<style>\n{css}\n</style>\n</head>\n"
        f'<body class="doc-{doc_type}">\n'
        + brand_block()
        + "\n".join(prelude)
        + body_fragment
        + "\n".join(tail)
        + "\n</body>\n</html>\n"
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="build.py",
        description="Build a branded Longhorn IP PDF from a Markdown body.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("body", help="Markdown file holding the body of the document")
    p.add_argument("--type", choices=TYPES, help="document type (default: report)")
    p.add_argument("--meta", help="JSON file with metadata")
    p.add_argument("--out", help="output PDF path (default: next to the Markdown file)")
    p.add_argument("--html-only", action="store_true", help="write the HTML, do not render a PDF")
    p.add_argument("--keep-html", action="store_true", help="keep the generated HTML next to the PDF")

    g = p.add_argument_group("metadata (overrides --meta)")
    g.add_argument("--title")
    g.add_argument("--subtitle")
    g.add_argument("--date")
    g.add_argument("--ref")
    g.add_argument("--subject")
    g.add_argument("--to", help="recipient lines, separated by | or newlines")
    g.add_argument("--from", dest="sender")
    g.add_argument("--attendees", help="names separated by | or newlines")
    g.add_argument("--apologies", help="names separated by | or newlines")
    g.add_argument("--location")
    g.add_argument("--time")
    g.add_argument("--chair")
    g.add_argument("--ai-note", action="store_true", help="append the AI-generated notice")

    s = p.add_argument_group("signature")
    s.add_argument("--signature-name")
    s.add_argument("--signature-role")
    s.add_argument("--signature-org")
    s.add_argument("--signature-contact", help="HTML allowed, e.g. 'www.x.com<br>+33 ...'")
    s.add_argument("--no-signature", action="store_true")

    return p.parse_args(argv)


def build_meta(args: argparse.Namespace) -> dict:
    meta: dict = {}
    if args.meta:
        path = Path(args.meta)
        if not path.exists():
            die(f"metadata file not found: {path}")
        meta = json.loads(path.read_text(encoding="utf-8"))

    for key in ("title", "subtitle", "date", "ref", "subject", "location", "time", "chair"):
        value = getattr(args, key, None)
        if value:
            meta[key] = value

    if args.type:
        meta["type"] = args.type
    if args.sender:
        meta["from"] = args.sender
    if args.to:
        meta["to"] = [x.strip() for x in re.split(r"[|\n]", args.to) if x.strip()]
    if args.attendees:
        meta["attendees"] = [x.strip() for x in re.split(r"[|\n]", args.attendees) if x.strip()]
    if args.apologies:
        meta["apologies"] = [x.strip() for x in re.split(r"[|\n]", args.apologies) if x.strip()]

    sig = dict(meta.get("signature") or {})
    if args.signature_name:
        sig["name"] = args.signature_name
    if args.signature_role:
        sig["role"] = args.signature_role
    if args.signature_org:
        sig["org"] = args.signature_org
    if args.signature_contact:
        sig["contact"] = args.signature_contact
    if args.no_signature:
        meta["signature"] = False
    elif sig:
        meta["signature"] = sig

    if args.ai_note:
        meta["ai_note"] = True

    meta.setdefault("type", "report")
    return meta


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    md_path = Path(args.body).expanduser().resolve()
    if not md_path.exists():
        die(f"markdown file not found: {md_path}")
    if not STYLE.exists():
        die(f"stylesheet missing: {STYLE}")

    meta = build_meta(args)
    if meta["type"] not in TYPES:
        die(f"unknown type: {meta['type']} (expected one of {', '.join(TYPES)})")

    body = absolutise_images(md_to_html(md_path), md_path.parent)
    document = compose(meta, body)

    out_pdf = Path(args.out).expanduser().resolve() if args.out else md_path.with_suffix(".pdf")
    out_html = out_pdf.with_suffix(".html")
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(document, encoding="utf-8")

    if args.html_only:
        print(f"HTML written: {out_html}")
        return 0

    require_tools()
    proc = subprocess.run(["weasyprint", str(out_html), str(out_pdf)], capture_output=True, text=True)
    if proc.returncode != 0:
        die(f"weasyprint failed:\n{proc.stderr.strip()}")

    if not args.keep_html:
        out_html.unlink(missing_ok=True)

    size_kb = out_pdf.stat().st_size / 1024
    print(f"{meta['type']}: {out_pdf} ({size_kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
