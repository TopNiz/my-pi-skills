#!/usr/bin/env python3
"""
Send an email via SMTP (Gmail).
Uses the same Keychain credentials as fetch_sent.py.

Supports both plain text and HTML formatted emails.

Usage:
    # Plain text (default)
    python3 send_email.py config.json <to> <subject> <body_file>

    # HTML formatted
    python3 send_email.py config.json <to> <subject> <body_file> --html

    # HTML with plain text fallback (best practice)
    python3 send_email.py config.json <to> <subject> <body_file> --html --alt <alt_text_file>

body_file: path to a file containing the email body (plain text or HTML)
"""

import smtplib
import email.utils
import html
import json
import os
import re
import subprocess
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def get_password(email_addr, service="email-manager"):
    """Retrieve password from macOS Keychain."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-a", email_addr, "-s", service, "-w"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        print(f"❌ Password not found in Keychain for {email_addr}")
        sys.exit(1)


def strip_html(html_content):
    """Convert HTML to plain text for fallback."""
    text = re.sub(r'<br\s*/?>', '\n', html_content, flags=re.IGNORECASE)
    text = re.sub(r'<p[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<li[^>]*>', '  • ', text, flags=re.IGNORECASE)
    text = re.sub(r'</li>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def is_html(content):
    """Check if content looks like HTML."""
    content_stripped = content.strip()
    return bool(re.search(r'<(html|body|div|p|br|table|h[1-6]|b|i|u|a|img|style|span)[^>]*>', content_stripped, re.IGNORECASE))


def main():
    args = sys.argv[1:]

    if len(args) < 4:
        print("Usage:")
        print("  python3 send_email.py config.json <to> <subject> <body_file> [--html] [--alt <alt_text_file>]")
        print("")
        print("Options:")
        print("  --html           Send as HTML (auto-detected if body contains HTML tags)")
        print("  --alt <file>     Plain text fallback for HTML emails (extracted from HTML if not provided)")
        sys.exit(1)

    config_path = args[0]
    to_email = args[1]
    subject = args[2]
    body_file = args[3]

    # Parse optional flags
    send_html = False
    alt_text_file = None
    requested_account = None
    remaining = args[4:]
    for i, arg in enumerate(remaining):
        if arg == '--html':
            send_html = True
        elif arg == '--alt' and i + 1 < len(remaining):
            alt_text_file = remaining[i + 1]
        elif arg == '--from-account' and i + 1 < len(remaining):
            requested_account = remaining[i + 1]

    if not os.path.exists(body_file):
        print(f"❌ Body file not found: {body_file}")
        sys.exit(1)

    with open(body_file, encoding='utf-8') as f:
        body = f.read()

    # Auto-detect HTML if not explicitly set
    if not send_html:
        send_html = is_html(body)

    with open(config_path) as f:
        config = json.load(f)

    # Use the first active account to send
    accounts_cfg = config.get("accounts", {})
    active = accounts_cfg.get("active", [])
    if not active:
        print("❌ No active accounts configured.")
        sys.exit(1)

    from_email = requested_account or active[0]
    acct = accounts_cfg["list"].get(from_email, {})
    if not acct:
        print(f"❌ Account not configured: {from_email}")
        sys.exit(1)

    imap_cfg = acct.get("imap", {})
    smtp_cfg = acct.get("smtp", {})
    username = smtp_cfg.get("username") or imap_cfg.get("username", from_email)

    pw_config = config.get("password_source", {})
    keychain_service = pw_config.get("service", "email-manager")
    password = get_password(from_email, keychain_service)

    smtp_server = smtp_cfg.get("server", "smtp.gmail.com")
    smtp_port = int(smtp_cfg.get("port", 587))
    smtp_use_ssl = bool(smtp_cfg.get("use_ssl", False))
    smtp_starttls = bool(smtp_cfg.get("starttls", not smtp_use_ssl))

    # Build message
    if send_html:
        # Get plain text fallback
        if alt_text_file and os.path.exists(alt_text_file):
            with open(alt_text_file, encoding='utf-8') as f:
                alt_text = f.read().strip()
        else:
            alt_text = strip_html(body)

        msg = MIMEMultipart('alternative')
        msg.attach(MIMEText(alt_text, 'plain', _charset='utf-8'))
        msg.attach(MIMEText(body, 'html', _charset='utf-8'))
        content_type = "HTML"
    else:
        msg = MIMEText(body, 'plain', _charset='utf-8')
        content_type = "plain text"

    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["Date"] = email.utils.formatdate(localtime=True)

    try:
        print(f"📤 Sending {content_type} email to {to_email}...")
        server_cls = smtplib.SMTP_SSL if smtp_use_ssl else smtplib.SMTP
        server = server_cls(smtp_server, smtp_port)
        if smtp_starttls and not smtp_use_ssl:
            server.starttls()
        server.login(username, password)
        server.sendmail(username, [to_email], msg.as_string())
        server.quit()
        print(f"✅ Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send: {e}")
        return False


if __name__ == "__main__":
    main()
