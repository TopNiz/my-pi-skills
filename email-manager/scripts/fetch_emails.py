#!/usr/bin/env python3
"""
Email Manager — Fetch Emails via Gmail API (OAuth2)
Part of the email-manager skill for pi.

Replaces the old IMAP-based fetcher. Uses Google's Gmail API for
faster, more reliable email access with OAuth2 authentication.

Usage:
  ./fetch_emails.py config.json [options]

Options:
  --days=N          Override fetch_days_back from config
  --max=N           Override max_emails from config
  --folder=FOLDER   Override folder (default: INBOX)
  --search=QUERY    Gmail search query (overrides date/folder filters)
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
import os
import re
import html
import base64
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

# Local auth module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auth import get_service, get_account_email

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
        if arg.startswith("--days="):
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


def decode_base64url(data):
    """Decode base64url-encoded data, padding if needed."""
    if data is None:
        return b""
    # Add padding if necessary
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    try:
        return base64.urlsafe_b64decode(data)
    except Exception:
        return base64.b64decode(data)


def decode_mime_header(value):
    """Decode a MIME-encoded header value (RFC 2047) to a plain string."""
    if not value:
        return ""
    # Handle RFC 2047 encoded words: =?charset?encoding?text?=
    parts = re.split(r"(=\?[^?]+\?[BbQq]\?[^?]*\?=)", value)
    result = []
    for part in parts:
        m = re.match(r"=\?([^?]+)\?([BbQq])\?([^?]*)\?=", part, re.IGNORECASE)
        if m:
            charset = m.group(1)
            encoding = m.group(2).upper()
            encoded_text = m.group(3)
            try:
                if encoding == "B":
                    decoded = base64.b64decode(encoded_text)
                else:
                    decoded = base64.b64decode(encoded_text.replace("_", "/"))
                result.append(decoded.decode(charset or "utf-8", errors="replace"))
            except Exception:
                result.append(encoded_text)
        else:
            result.append(part)
    return " ".join(result).strip()


def get_header(headers, name):
    """Extract a header value from the Gmail API headers list."""
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def extract_body_and_attachments(payload):
    """
    Recursively extract plain text body and attachment metadata
    from a Gmail API message payload.
    """
    body_text = ""
    attachments = []
    mime_type = payload.get("mimeType", "")
    filename = payload.get("filename", "")

    # Is this an attachment?
    if filename:
        body_size = payload.get("body", {}).get("size", 0)
        attachments.append({
            "filename": filename,
            "size": body_size,
            "type": mime_type
        })
        return body_text, attachments

    # Has body data directly
    body_data = payload.get("body", {}).get("data")
    if body_data and mime_type == "text/plain":
        try:
            body_text = decode_base64url(body_data).decode("utf-8", errors="replace")
        except Exception:
            body_text = body_data  # fallback
    elif body_data and mime_type == "text/html" and not body_text:
        try:
            html_content = decode_base64url(body_data).decode("utf-8", errors="replace")
            text = re.sub(r"<[^>]+>", " ", html_content)
            text = html.unescape(text)
            text = re.sub(r"\s+", " ", text).strip()
            body_text = text
        except Exception:
            pass

    # Process parts recursively
    for part in payload.get("parts", []):
        part_body, part_attachments = extract_body_and_attachments(part)
        if part_body and not body_text:
            body_text = part_body
        attachments.extend(part_attachments)

    return body_text, attachments


def build_gmail_query(filters, folder, custom_search=None):
    """
    Build a Gmail API search query (q parameter) from config filters.
    """
    if custom_search:
        return custom_search

    parts = []

    # Folder = label
    if folder and folder != "INBOX":
        parts.append(f"label:{folder}")
    elif folder == "INBOX":
        parts.append("in:inbox")

    # Date filter
    days_back = filters.get("fetch_days_back", 7)
    since_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y/%m/%d")
    parts.append(f"after:{since_date}")

    # Seen/unseen filter
    if not filters.get("include_seen", False):
        parts.append("is:unread")

    return " ".join(parts)


def get_label_info(service, label_id="INBOX"):
    """Get label name and message counts from Gmail API."""
    try:
        label = service.users().labels().get(userId="me", id=label_id).execute()
        return {
            "total": label.get("messagesTotal", 0),
            "unread": label.get("messagesUnread", 0),
            "name": label.get("name", label_id)
        }
    except Exception:
        return {"total": 0, "unread": 0, "name": label_id}


def fetch_account_emails(service, account_email, filters, custom_search=None):
    """
    Fetch emails using Gmail API for one account.
    Returns the same JSON structure as the old IMAP version for compatibility.
    """
    max_emails = filters.get("max_emails", 50)
    folders = filters.get("folders", ["INBOX"])

    result = {
        "account": account_email,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total": 0,
        "unread": 0,
        "folders": {}
    }

    try:
        for folder in folders:
            folder_emails = []
            label_info = get_label_info(service, folder)

            # Build search query
            query = build_gmail_query(filters, folder, custom_search)

            # List messages matching query
            try:
                response = service.users().messages().list(
                    userId="me",
                    q=query,
                    maxResults=max_emails,
                    labelIds=[folder] if folder != "INBOX" else []
                ).execute()
            except Exception as e:
                result["folders"][folder] = {
                    "error": f"Gmail API search error: {str(e)}",
                    "total": label_info["total"],
                    "unread": label_info["unread"],
                    "emails": []
                }
                continue

            messages = response.get("messages", [])

            # Fetch details for each message
            for msg_ref in messages:
                msg_id = msg_ref.get("id")
                if not msg_id:
                    continue

                try:
                    full_msg = service.users().messages().get(
                        userId="me", id=msg_id, format="full"
                    ).execute()
                except Exception:
                    continue

                payload = full_msg.get("payload", {})
                headers = payload.get("headers", [])

                # Extract headers
                subject = decode_mime_header(get_header(headers, "Subject")) or "(no subject)"
                from_ = decode_mime_header(get_header(headers, "From")) or "(unknown)"
                date_str = get_header(headers, "Date")
                message_id = get_header(headers, "Message-ID")
                references = get_header(headers, "References")
                in_reply_to = get_header(headers, "In-Reply-To")

                # Parse date
                try:
                    if date_str:
                        date_dt = parsedate_to_datetime(date_str)
                        date_iso = date_dt.isoformat()
                    else:
                        # Fallback to internal date
                        internal_date = full_msg.get("internalDate", "")
                        if internal_date:
                            date_dt = datetime.fromtimestamp(
                                int(internal_date) / 1000, tz=timezone.utc
                            )
                            date_iso = date_dt.isoformat()
                        else:
                            date_iso = date_str
                except Exception:
                    date_iso = date_str

                # Extract body and attachments
                body_text, attachments = extract_body_and_attachments(payload)

                # Snippet
                snippet = full_msg.get("snippet", "(no content)")

                # Parse label IDs into flags
                label_ids = full_msg.get("labelIds", [])
                flag_list = []
                if "UNREAD" in label_ids:
                    flag_list.append("\\Seen")
                if "STARRED" in label_ids:
                    flag_list.append("\\Flagged")
                if "IMPORTANT" in label_ids:
                    flag_list.append("\\Important")

                email_data = {
                    "uid": msg_id,
                    "message_id": message_id or in_reply_to or "",
                    "date": date_iso,
                    "from": from_,
                    "subject": subject,
                    "snippet": snippet,
                    "body_text": body_text[:5000] if body_text else "",
                    "has_attachments": len(attachments) > 0,
                    "attachments": attachments,
                    "flags": flag_list,
                    "_gmail_labels": label_ids,  # Extra info for Gmail API
                    "thread_id": full_msg.get("threadId", "")
                }

                folder_emails.append(email_data)

            result["folders"][folder] = {
                "total": label_info["total"],
                "unread": label_info["unread"],
                "emails": folder_emails
            }

            result["total"] += label_info["total"]
            result["unread"] += label_info["unread"]

    except Exception as e:
        return {"error": f"Gmail API error: {str(e)}", "account": account_email}

    return result


def main():
    if not CONFIG_PATH:
        print(__doc__)
        sys.exit(1)

    config = load_config(CONFIG_PATH)
    config = parse_args(config)

    # Get authenticated Gmail API service
    try:
        service = get_service()
        account_email = get_account_email(service)
    except Exception as e:
        print(json.dumps({
            "error": f"Authentication failed: {str(e)}. Run 'python3 scripts/auth.py' first."
        }), file=sys.stderr)
        sys.exit(1)

    # Build filters from config + CLI overrides
    filters = config.get("filters", {})
    if "fetch_days_back" in config.get("filters", {}):
        filters["fetch_days_back"] = config["filters"]["fetch_days_back"]
    if "max_emails" in config.get("filters", {}):
        filters["max_emails"] = config["filters"]["max_emails"]
    if "folders" in config.get("filters", {}):
        filters["folders"] = config["filters"]["folders"]

    search_override = config.get("_search")

    # Check if account is requested (single-account Gmail, so mostly for compat)
    cli_account = config.get("_account")
    if cli_account and cli_account.lower() != account_email.lower():
        print(json.dumps({
            "error": f"Authenticated as {account_email}, but --account={cli_account} requested."
        }), file=sys.stderr)
        sys.exit(1)

    result = fetch_account_emails(service, account_email, filters, search_override)

    # Wrap in multi-account format for backward compat
    output = {"accounts": [result]}
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
