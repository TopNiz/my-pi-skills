#!/usr/bin/env python3
"""
Email Manager — Fetch Emails via IMAP
Part of the email-manager skill for pi.

Usage:
  ./fetch_emails.py config.json [options]

Options:
  --mode=MODE       fetch | inbox | search | attachments
  --days=N          Override fetch_days_back from config
  --max=N           Override max_emails from config
  --folder=FOLDER   Override folder (default: INBOX)
  --search=QUERY    IMAP search query (e.g. "FROM example.com SINCE 1-May-2026")
  --help            Show this message

Output: JSON to stdout with structure:
  {
    "account": "...",
    "total": N,
    "unread": N,
    "emails": [
      {
        "uid": "...",
        "message_id": "...",
        "date": "ISO datetime",
        "from": "Name <email>",
        "subject": "...",
        "snippet": "First 200 chars of body",
        "has_attachments": true/false,
        "attachments": [{"filename": "invoice.pdf", "size": 12345, "type": "application/pdf"}],
        "body_text": "Full plain text or stripped HTML (truncated to 5000 chars)",
        "flags": ["\\Seen", "\\Flagged"]
      }
    ]
  }
"""

import json
import sys
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta, timezone
import html
import re
import os
import base64
import quopri

CONFIG_PATH = sys.argv[1] if len(sys.argv) > 1 else None


def load_config(path):
    if not path or not os.path.exists(path):
        print(json.dumps({"error": f"Config file not found: {path}"}), file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def parse_args(config):
    """Parse CLI args and merge with config."""
    cfg = config.copy()
    for arg in sys.argv[2:]:
        if arg.startswith("--mode="):
            cfg["_mode"] = arg.split("=", 1)[1]
        elif arg.startswith("--days="):
            cfg["filters"]["fetch_days_back"] = int(arg.split("=", 1)[1])
        elif arg.startswith("--max="):
            cfg["filters"]["max_emails"] = int(arg.split("=", 1)[1])
        elif arg.startswith("--folder="):
            cfg["filters"]["folders"] = [arg.split("=", 1)[1]]
        elif arg.startswith("--search="):
            cfg["_search"] = arg.split("=", 1)[1]
        elif arg == "--help":
            print(__doc__)
            sys.exit(0)
    return cfg


def decode_mime_header(value):
    """Decode a MIME-encoded header value to a plain string."""
    if not value:
        return ""
    parts = decode_header(value)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            try:
                result.append(part.decode(charset or "utf-8", errors="replace"))
            except (LookupError, UnicodeDecodeError):
                result.append(part.decode("utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def get_body(msg):
    """Extract plain text body and attachment info from an email message."""
    body_text = ""
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disp = str(part.get("Content-Disposition", ""))
            filename = part.get_filename()

            if filename:
                fname = decode_mime_header(filename)
                # Decode attachment payload
                payload = part.get_payload(decode=True)
                if payload is None:
                    payload = b""
                attachments.append({
                    "filename": fname,
                    "size": len(payload),
                    "type": content_type
                })
            elif content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        body_text += payload.decode(charset, errors="replace")
                    except (LookupError, UnicodeDecodeError):
                        body_text += payload.decode("utf-8", errors="replace")
            elif content_type == "text/html" and not body_text:
                # Use HTML only if no plain text found
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        html_content = payload.decode(charset, errors="replace")
                    except (LookupError, UnicodeDecodeError):
                        html_content = payload.decode("utf-8", errors="replace")
                    # Strip HTML tags
                    text = re.sub(r"<[^>]+>", " ", html_content)
                    text = html.unescape(text)
                    text = re.sub(r"\s+", " ", text).strip()
                    body_text = text
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            try:
                body_text = payload.decode(charset, errors="replace")
            except (LookupError, UnicodeDecodeError):
                body_text = payload.decode("utf-8", errors="replace")

    return body_text.strip(), attachments


def build_search_criteria(config, folder="INBOX"):
    """Build IMAP search criteria based on config."""
    filters = config.get("filters", {})
    days_back = filters.get("fetch_days_back", 7)
    include_seen = filters.get("include_seen", False)
    custom_search = config.get("_search")

    criteria = []

    if custom_search:
        return [custom_search]

    # Date filter
    since_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%d-%b-%Y")
    criteria.append(f'SINCE {since_date}')

    # Seen/unseen filter
    if not include_seen:
        criteria.append("UNSEEN")

    return criteria


def fetch_emails(config):
    """Connect to IMAP and fetch emails."""
    imap_cfg = config["imap"]
    filters = config.get("filters", {})
    max_emails = filters.get("max_emails", 50)
    folders = filters.get("folders", ["INBOX"])
    _mode = config.get("_mode", "fetch")

    results = {
        "account": imap_cfg.get("username", "unknown"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total": 0,
        "unread": 0,
        "folders": {}
    }

    try:
        # Connect
        if imap_cfg.get("use_ssl", True):
            mail = imaplib.IMAP4_SSL(imap_cfg["server"], imap_cfg.get("port", 993))
        else:
            mail = imaplib.IMAP4(imap_cfg["server"], imap_cfg.get("port", 143))
        
        mail.login(imap_cfg["username"], imap_cfg["password"])

        for folder in folders:
            folder_emails = []
            status, _ = mail.select(folder)
            if status != "OK":
                results["folders"][folder] = {"error": f"Cannot select folder: {folder}"}
                continue

            # Get total messages
            status, data = mail.search(None, "ALL")
            if status != "OK":
                results["folders"][folder] = {"error": "Search failed"}
                continue

            total_in_folder = len(data[0].split()) if data[0] else 0

            # Get unread count
            status, unread_data = mail.search(None, "UNSEEN")
            unread_in_folder = len(unread_data[0].split()) if unread_data[0] else 0

            # Build search criteria
            search_criteria = build_search_criteria(config, folder)
            status, msg_ids = mail.uid("SEARCH", None, *search_criteria)

            if status != "OK" or not msg_ids[0]:
                results["folders"][folder] = {
                    "total": total_in_folder,
                    "unread": unread_in_folder,
                    "emails": []
                }
                continue

            # Get UIDs (most recent first)
            uids = msg_ids[0].split()
            uids.reverse()
            uids = uids[:max_emails]

            for uid in uids:
                status, msg_data = mail.uid("FETCH", uid, "(FLAGS BODY.PEEK[])")
                if status != "OK":
                    continue

                for part in msg_data:
                    if isinstance(part, tuple):
                        raw_email = part[1]
                        flags = part[0]
                        break
                else:
                    continue

                msg = email.message_from_bytes(raw_email)
                
                # Parse email
                subject = decode_mime_header(msg.get("Subject", "(no subject)"))
                from_ = decode_mime_header(msg.get("From", "(unknown)"))
                date_str = msg.get("Date", "")
                message_id = msg.get("Message-ID", "")
                references = msg.get("References", "")

                try:
                    date_dt = parsedate_to_datetime(date_str)
                    date_iso = date_dt.isoformat()
                except Exception:
                    date_iso = date_str

                body_text, attachments = get_body(msg)
                snippet = body_text[:200].replace("\n", " ") if body_text else "(no content)"

                # Parse flags
                flag_list = []
                if isinstance(flags, bytes):
                    flags_str = flags.decode("utf-8", errors="replace")
                    if "\\Seen" in flags_str:
                        flag_list.append("\\Seen")
                    if "\\Flagged" in flags_str:
                        flag_list.append("\\Flagged")
                    if "\\Answered" in flags_str:
                        flag_list.append("\\Answered")

                email_data = {
                    "uid": uid.decode() if isinstance(uid, bytes) else str(uid),
                    "message_id": message_id,
                    "date": date_iso,
                    "from": from_,
                    "subject": subject,
                    "snippet": snippet,
                    "body_text": body_text[:5000] if body_text else "",
                    "has_attachments": len(attachments) > 0,
                    "attachments": attachments,
                    "flags": flag_list
                }

                folder_emails.append(email_data)

            results["folders"][folder] = {
                "total": total_in_folder,
                "unread": unread_in_folder,
                "emails": folder_emails
            }

            results["total"] += total_in_folder
            results["unread"] += unread_in_folder

        mail.logout()

    except imaplib.IMAP4.error as e:
        return {"error": f"IMAP error: {str(e)}", "account": imap_cfg.get("username", "unknown")}
    except Exception as e:
        return {"error": f"Connection error: {str(e)}", "account": imap_cfg.get("username", "unknown")}

    return results


def main():
    if not CONFIG_PATH:
        print(__doc__)
        sys.exit(1)
    
    config = load_config(CONFIG_PATH)
    config = parse_args(config)
    
    result = fetch_emails(config)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
