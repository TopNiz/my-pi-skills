#!/usr/bin/env python3
"""
Email Manager — Fetch Emails via IMAP (Multi-Account + macOS Keychain)
Part of the email-manager skill for pi.

Usage:
  ./fetch_emails.py config.json [options]

Options:
  --mode=MODE       fetch | inbox | search | attachments
  --days=N          Override fetch_days_back from config
  --max=N           Override max_emails from config
  --folder=FOLDER   Override folder (default: INBOX)
  --search=QUERY    IMAP search query
  --account=EMAIL   Fetch only one account (email address)
  --help            Show this message

Output: JSON to stdout with structure:
  {
    "accounts": [
      {
        "account": "...",
        "fetched_at": "...",
        "total": N,
        "unread": N,
        "folders": {
          "INBOX": {
            "total": N,
            "unread": N,
            "emails": [...]
          }
        }
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
import subprocess
import base64
import quopri

CONFIG_PATH = sys.argv[1] if len(sys.argv) > 1 else None


def get_password_from_keychain(account, service="email-manager"):
    """Retrieve a password from macOS Keychain."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-a", account, "-s", service, "-w"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(json.dumps({
            "error": f"Failed to get password from Keychain for {account}: {e.stderr.strip()}"
        }), file=sys.stderr)
        sys.exit(1)


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
            cfg.setdefault("filters", {})["fetch_days_back"] = int(arg.split("=", 1)[1])
        elif arg.startswith("--max="):
            cfg.setdefault("filters", {})["max_emails"] = int(arg.split("=", 1)[1])
        elif arg.startswith("--folder="):
            cfg.setdefault("filters", {})["folders"] = [arg.split("=", 1)[1]]
        elif arg.startswith("--search="):
            cfg["_search"] = arg.split("=", 1)[1]
        elif arg.startswith("--account="):
            cfg["_account"] = arg.split("=", 1)[1]
        elif arg == "--help":
            print(__doc__)
            sys.exit(0)
    return cfg


def get_accounts_to_process(config):
    """Return list of account dicts to process based on config and CLI args."""
    accounts_cfg = config.get("accounts", {})
    active_emails = accounts_cfg.get("active", [])
    accounts_list = accounts_cfg.get("list", {})
    cli_account = config.get("_account")

    # Legacy fallback: if no accounts config, use top-level imap
    if not active_emails and "imap" in config:
        fallback = config["imap"].copy()
        fallback["_password"] = fallback.get("password", "")
        fallback["_filters"] = config.get("filters", {})
        fallback["_invoices"] = config.get("invoices", {})
        return [(config["imap"]["username"], fallback)]

    # Filter by --account if specified
    if cli_account:
        if cli_account not in accounts_list:
            print(json.dumps({"error": f"Account '{cli_account}' not found in config.accounts.list"}), file=sys.stderr)
            sys.exit(1)
        active_emails = [cli_account]

    results = []
    for email_addr in active_emails:
        if email_addr not in accounts_list:
            continue
        acct = accounts_list[email_addr].copy()
        imap_cfg = acct.get("imap", {}).copy()

        # Get password from Keychain
        keychain_service = config.get("password_source", {}).get("service", "email-manager")
        password = get_password_from_keychain(email_addr, keychain_service)

        imap_cfg["password"] = password
        imap_cfg["_filters"] = acct.get("filters", {})
        imap_cfg["_invoices"] = acct.get("invoices", {})

        results.append((email_addr, imap_cfg))

    return results


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
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        html_content = payload.decode(charset, errors="replace")
                    except (LookupError, UnicodeDecodeError):
                        html_content = payload.decode("utf-8", errors="replace")
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


def build_search_criteria(filters, custom_search=None):
    """Build IMAP search criteria based on config."""
    days_back = filters.get("fetch_days_back", 7)
    include_seen = filters.get("include_seen", False)

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


def fetch_account_emails(email_addr, imap_cfg, filters, search_override=None):
    """Connect to IMAP and fetch emails for one account."""
    max_emails = filters.get("max_emails", 50)
    folders = filters.get("folders", ["INBOX"])
    _mode = search_override

    result = {
        "account": email_addr,
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
                result["folders"][folder] = {"error": f"Cannot select folder: {folder}"}
                continue

            # Get total messages
            status, data = mail.search(None, "ALL")
            if status != "OK":
                result["folders"][folder] = {"error": "Search failed"}
                continue

            total_in_folder = len(data[0].split()) if data[0] else 0

            # Get unread count
            status, unread_data = mail.search(None, "UNSEEN")
            unread_in_folder = len(unread_data[0].split()) if unread_data[0] else 0

            # Build search criteria
            search_criteria = build_search_criteria(filters, search_override)
            status, msg_ids = mail.uid("SEARCH", None, *search_criteria)

            if status != "OK" or not msg_ids[0]:
                result["folders"][folder] = {
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

            result["folders"][folder] = {
                "total": total_in_folder,
                "unread": unread_in_folder,
                "emails": folder_emails
            }

            result["total"] += total_in_folder
            result["unread"] += unread_in_folder

        mail.logout()

    except imaplib.IMAP4.error as e:
        return {"error": f"IMAP error: {str(e)}", "account": email_addr}
    except Exception as e:
        return {"error": f"Connection error: {str(e)}", "account": email_addr}

    return result


def main():
    if not CONFIG_PATH:
        print(__doc__)
        sys.exit(1)

    config = load_config(CONFIG_PATH)
    config = parse_args(config)

    accounts = get_accounts_to_process(config)
    results = {"accounts": []}

    for email_addr, imap_cfg in accounts:
        filters = imap_cfg.pop("_filters", config.get("filters", {}))
        search_override = config.get("_search")

        # Merge global CLI overrides
        if "fetch_days_back" in config.get("filters", {}):
            filters["fetch_days_back"] = config["filters"]["fetch_days_back"]
        if "max_emails" in config.get("filters", {}):
            filters["max_emails"] = config["filters"]["max_emails"]
        if "folders" in config.get("filters", {}):
            filters["folders"] = config["filters"]["folders"]

        account_result = fetch_account_emails(email_addr, imap_cfg, filters, search_override)
        results["accounts"].append(account_result)

    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
