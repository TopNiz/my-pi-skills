#!/usr/bin/env python3
"""
Send an email with a PDF attachment via Gmail SMTP.
Reads password from macOS Keychain (service: email-manager).
"""

import smtplib
import subprocess
import sys
import os
from email.message import EmailMessage
from email.utils import formatdate

# ── Configuration ──
SMTP_SERVER = "imap.gmail.com"  # We'll use smtp.gmail.com below
SMTP_PORT = 587
FROM_EMAIL = "nizar.ayed@chain-it.com"
KEYCHAIN_SERVICE = "email-manager"


def get_password(account: str) -> str:
    """Get password from macOS Keychain."""
    result = subprocess.run(
        ["security", "find-generic-password", "-a", account, "-s", KEYCHAIN_SERVICE, "-w"],
        capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def send_email(to: str, subject: str, body_html: str, pdf_path: str | None = None) -> bool:
    """Send email via Gmail SMTP with optional PDF attachment."""
    password = get_password(FROM_EMAIL)

    msg = EmailMessage()
    msg["From"] = FROM_EMAIL
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)

    # Plain text fallback (strip HTML tags)
    import re as _re
    plain = _re.sub(r'<[^>]+>', '', body_html)
    plain = _re.sub(r'\s+', ' ', plain).strip()
    msg.set_content(plain)

    # HTML version
    msg.add_alternative(body_html, subtype='html')

    # Attach PDF if provided
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        pdf_name = os.path.basename(pdf_path)
        msg.add_attachment(
            pdf_data,
            maintype="application",
            subtype="pdf",
            filename=pdf_name,
        )

    # Send via Gmail SMTP
    try:
        with smtplib.SMTP("smtp.gmail.com", SMTP_PORT) as server:
            server.starttls()
            server.login(FROM_EMAIL, password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"❌ Email send failed: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: send_email_report.py TO_EMAIL SUBJECT BODY_FILE [PDF_FILE]", file=sys.stderr)
        sys.exit(1)

    to_email = sys.argv[1]
    subject = sys.argv[2]
    body_file = sys.argv[3]
    pdf_file = sys.argv[4] if len(sys.argv) > 4 else None

    if not os.path.exists(body_file):
        print(f"❌ Body file not found: {body_file}", file=sys.stderr)
        sys.exit(1)

    with open(body_file) as f:
        body = f.read()

    success = send_email(to_email, subject, body, pdf_file)
    if success:
        print(f"✅ Report email sent to {to_email}")
    else:
        sys.exit(1)
