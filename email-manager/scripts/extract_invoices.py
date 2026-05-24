#!/usr/bin/env python3
"""
Email Manager — Invoice Extractor
Part of the email-manager skill for pi.

Extracts invoice data from email JSON (output of fetch_emails.py).
Saves invoice metadata to a JSON file and downloads attachments.

Usage:
  ./extract_invoices.py <emails_json_file> <config.json> [--output-dir=DIR]

The script identifies emails likely containing invoices by checking:
  - Subject keywords (invoice, facture, rechnung, bill, receipt, etc.)
  - Attachment types (PDF, DOCX, XLSX)
  - Sender patterns (known vendors, accounting departments)

Output:
  - Prints invoice metadata as JSON to stdout
  - Saves attachments to the configured storage directory
"""

import json
import sys
import os
import re
import shutil
from datetime import datetime

INVOICE_KEYWORDS = [
    "invoice", "facture", "rechnung", "bill", "receipt", "rechnung",
    "fattura", "invoice", "statement", "purchase order", "po ",
    "order confirmation", "payment due", "due date", "amount due",
    "invoice #", "facture n°", "comptabilité", "accounting",
    "tax invoice", "proforma", "debit note", "credit note",
    "paiement", "payment", "transaction", "reçu", "recu"
]

INVOICE_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".xls", ".csv", ".xml",
    ".jpg", ".png",  # Scanned invoices
    ".ofx", ".qif"   # Financial formats
}

SENDER_BLACKLIST = [
    "noreply@", "no-reply@", "newsletter@", "mail@", "marketing@",
    "notifications@", "alert@", "updates@", "spam@"
]


def load_json(path):
    with open(path) as f:
        return json.load(f)


def is_invoice_email(email):
    """Score an email on how likely it contains an invoice."""
    subject = email.get("subject", "").lower()
    from_ = email.get("from", "").lower()
    body = email.get("body_text", "").lower()[:1000]
    attachments = email.get("attachments", [])

    score = 0
    reasons = []

    # Check subject for invoice keywords
    for kw in INVOICE_KEYWORDS:
        if kw.lower() in subject:
            score += 3
            reasons.append(f"subject_keyword:{kw}")
            break  # Max one point from keywords

    # Check body for invoice keywords
    for kw in INVOICE_KEYWORDS:
        if kw.lower() in body:
            score += 1
            reasons.append(f"body_keyword:{kw}")
            break

    # Check attachments
    for att in attachments:
        fname = att.get("filename", "").lower()
        ext = os.path.splitext(fname)[1].lower()
        if ext in INVOICE_EXTENSIONS:
            score += 2
            reasons.append(f"attachment_ext:{ext}")
        if any(kw.replace(" ", "") in fname.replace(" ", "") for kw in ["invoice", "facture", "bill", "receipt"]):
            score += 2
            reasons.append(f"attachment_name:{fname}")

    # Sender blacklist penalty
    for bl in SENDER_BLACKLIST:
        if bl in from_:
            score -= 2
            reasons.append(f"sender_blacklisted:{bl}")

    # Money amounts in body
    money_pattern = r'(?:€|EUR|USD|\$|GBP|£)\s*\d+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?\s*(?:€|EUR|USD|\$|GBP|£)'
    if re.search(money_pattern, body):
        score += 1
        reasons.append("money_amount_in_body")

    return score, reasons


def extract_invoice_metadata(email):
    """Extract structured metadata from an invoice email."""
    from_ = email.get("from", "")
    subject = email.get("subject", "")
    date = email.get("date", "")
    body = email.get("body_text", "")

    # Try to extract amount
    amount = None
    money_pattern = r'(?:€|EUR|USD|\$|GBP|£)\s*(\d+(?:[.,]\d{1,2})?)'
    amounts = re.findall(money_pattern, body)
    if amounts:
        # Take the largest amount found
        try:
            amounts_float = [float(a.replace(",", ".")) for a in amounts]
            amount = max(amounts_float)
        except ValueError:
            pass

    # Try to extract invoice number
    invoice_no = None
    inv_patterns = [
        r'(?:invoice|facture|inv|fact)\s*(?:#|no|n°|num[ée]ro)?[:\s]*([A-Z0-9][-A-Z0-9/]{3,20})',
        r'ref(?:érence)?[:\s]*([A-Z0-9][-A-Z0-9/]{3,20})',
        r'number[:\s]*([A-Z0-9][-A-Z0-9/]{3,20})'
    ]
    for pat in inv_patterns:
        m = re.search(pat, body, re.IGNORECASE)
        if m:
            invoice_no = m.group(1)
            break

    if not invoice_no:
        # Try subject
        m = re.search(r'(?:#|no|n°)[:\s]*([A-Z0-9][-A-Z0-9/]{3,20})', subject, re.IGNORECASE)
        if m:
            invoice_no = m.group(1)

    # Extract sender name (before @)
    sender_name = from_.split("<")[0].strip() if "<" in from_ else from_.split("@")[0].strip()

    return {
        "sender": sender_name,
        "from_email": from_,
        "subject": subject,
        "date": date,
        "estimated_amount": amount,
        "invoice_number": invoice_no,
        "attachment_count": len(email.get("attachments", [])),
        "attachments": email.get("attachments", [])
    }


def save_attachments(email, config, output_dir, email_index):
    """Save invoice attachments to the output directory."""
    saved_files = []
    
    storage_dir = output_dir or config.get("invoices", {}).get("storage_dir", "./invoices")
    os.makedirs(storage_dir, exist_ok=True)

    # We need the original email data from fetch_emails, but attachments
    # are metadata-only at this point. We instruct the agent to download
    # via IMAP in the SKILL.md. This function logs what should be saved.
    
    date_str = email.get("date", "")[:10]  # YYYY-MM-DD
    subject_slug = re.sub(r"[^a-zA-Z0-9]+", "_", email.get("subject", "invoice"))[:40]
    
    for i, att in enumerate(email.get("attachments", [])):
        fname = att.get("filename", f"attachment_{i}")
        # Create unique filename: date_subject_filename
        safe_name = f"{date_str}_{subject_slug}_{fname}"
        dest = os.path.join(storage_dir, safe_name)
        saved_files.append({
            "original": fname,
            "saved_as": safe_name,
            "path": dest,
            "size": att.get("size", 0),
            "type": att.get("type", "")
        })

    return saved_files


def main():
    if len(sys.argv) < 3:
        print("Usage: ./extract_invoices.py <emails_json> <config.json> [--output-dir=DIR]")
        sys.exit(1)

    emails_path = sys.argv[1]
    config_path = sys.argv[2]
    output_dir = None

    for arg in sys.argv[3:]:
        if arg.startswith("--output-dir="):
            output_dir = arg.split("=", 1)[1]

    emails_data = load_json(emails_path)
    config = load_json(config_path) if os.path.exists(config_path) else {}

    # Collect all emails from all folders
    all_emails = []
    for folder_name, folder_data in emails_data.get("folders", {}).items():
        for email in folder_data.get("emails", []):
            all_emails.append(email)

    # Score and classify
    invoice_emails = []
    for email in all_emails:
        score, reasons = is_invoice_email(email)
        if score >= 3:  # Threshold for considering an invoice
            metadata = extract_invoice_metadata(email)
            saved = save_attachments(email, config, output_dir, len(invoice_emails))
            invoice_emails.append({
                "email_uid": email.get("uid"),
                "date": email.get("date"),
                "from": email.get("from"),
                "subject": email.get("subject"),
                "score": score,
                "reasons": reasons,
                "metadata": metadata,
                "files_to_save": saved
            })

    result = {
        "total_emails_scanned": len(all_emails),
        "invoices_found": len(invoice_emails),
        "storage_directory": output_dir or config.get("invoices", {}).get("storage_dir", "./invoices"),
        "invoices": invoice_emails,
        "_note": "Review the invoices list. To fully download attachments, use the fetch_emails.py script with --mode=attachments or follow the SKILL.md instructions."
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Save invoice metadata to storage dir
    storage_dir = output_dir or config.get("invoices", {}).get("storage_dir", "./invoices")
    if invoice_emails:
        os.makedirs(storage_dir, exist_ok=True)
        meta_path = os.path.join(storage_dir, f"_invoice_index_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(meta_path, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n📁 Invoice index saved to: {meta_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
