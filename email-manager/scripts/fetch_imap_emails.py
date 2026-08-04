#!/usr/bin/env python3
"""Read email through an SSL IMAP account configured in config.json.

Credentials are retrieved from macOS Keychain and are never stored in config.
"""

import argparse
import email
import imaplib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from email.policy import default
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path


def keychain_password(service, account):
    result = subprocess.run(
        ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("IMAP credential is unavailable in macOS Keychain")
    return result.stdout.decode().rstrip("\r\n")


def resolve_imap_profile(config, requested_account):
    """Resolve IMAP and Keychain metadata without accepting inline secrets."""
    profile = config.get("accounts", {}).get("list", {}).get(requested_account)
    if profile:
        if profile.get("transport", "imap") != "imap":
            raise RuntimeError("Requested account has no IMAP profile")
        settings = profile.get("imap", {})
        filters = profile.get("filters", config.get("filters", {}))
        password_source = profile.get("password_source", config.get("password_source", {}))
    else:
        settings = config.get("imap", {})
        username = settings.get("username", "")
        if not settings or username.lower() != requested_account.lower():
            raise RuntimeError("Requested account has no IMAP profile")
        filters = config.get("filters", {})
        password_source = config.get("password_source", {})

    if "password" in settings:
        raise RuntimeError("Inline IMAP credentials are not supported")

    method = password_source.get("method", "keychain")
    if method != "keychain":
        raise RuntimeError("Unsupported IMAP credential source")

    username = settings.get("username", requested_account)
    service = settings.get("keychain_service", password_source.get("service", "email-manager"))
    credential_account = settings.get("keychain_account", username)
    return settings, filters, username, service, credential_account


def decoded(value):
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def plain_body(message):
    plain = []
    html = []
    parts = message.walk() if message.is_multipart() else [message]
    for part in parts:
        if part.get_content_disposition() == "attachment":
            continue
        content_type = part.get_content_type()
        if content_type not in {"text/plain", "text/html"}:
            continue
        try:
            text = part.get_content()
        except Exception:
            payload = part.get_payload(decode=True) or b""
            text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        (plain if content_type == "text/plain" else html).append(text)
    if plain:
        return "\n".join(plain).strip()
    text = " ".join(html)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def attachments(message):
    items = []
    for part in message.walk():
        filename = part.get_filename()
        if filename:
            payload = part.get_payload(decode=True) or b""
            items.append({
                "filename": decoded(filename),
                "size": len(payload),
                "type": part.get_content_type(),
            })
    return items


def imap_date(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%d-%b-%Y")


def fetch(config_path, account, query, maximum, days):
    config = json.loads(Path(config_path).read_text())
    settings, filters, username, service, credential_account = resolve_imap_profile(
        config, account
    )
    maximum = maximum or int(filters.get("max_emails", 50))
    days = days or int(filters.get("fetch_days_back", 30))
    password = keychain_password(service, credential_account)

    client_cls = imaplib.IMAP4_SSL if settings.get("use_ssl", True) else imaplib.IMAP4
    client = client_cls(settings["server"], int(settings.get("port", 993)))
    try:
        try:
            client.login(username, password)
        finally:
            password = ""
        status, _ = client.select("INBOX", readonly=True)
        if status != "OK":
            raise RuntimeError("Unable to open IMAP inbox")

        criteria = ["SINCE", imap_date(days)]
        if query:
            criteria.extend(["TEXT", f'"{query}"'])
        status, data = client.uid("search", None, *criteria)
        if status != "OK":
            raise RuntimeError("IMAP search failed")
        uids = data[0].split()[-maximum:]

        messages = []
        for uid in reversed(uids):
            status, fetched = client.uid("fetch", uid, "(RFC822 FLAGS)")
            if status != "OK" or not fetched or not isinstance(fetched[0], tuple):
                continue
            raw = fetched[0][1]
            message = email.message_from_bytes(raw, policy=default)
            body = plain_body(message)
            files = attachments(message)
            date_value = message.get("Date", "")
            try:
                date_value = parsedate_to_datetime(date_value).isoformat()
            except Exception:
                pass
            messages.append({
                "uid": uid.decode(),
                "message_id": message.get("Message-ID", ""),
                "date": date_value,
                "from": decoded(message.get("From", "")),
                "to": decoded(message.get("To", "")),
                "cc": decoded(message.get("Cc", "")),
                "subject": decoded(message.get("Subject", "")) or "(no subject)",
                "snippet": re.sub(r"\s+", " ", body)[:300],
                "body_text": body[:10000],
                "has_attachments": bool(files),
                "attachments": files,
            })
        return {"accounts": [{"account": account, "emails": messages, "matched": len(messages)}]}
    finally:
        try:
            client.logout()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("--account", required=True)
    parser.add_argument("--query", default="")
    parser.add_argument("--max", type=int, default=0)
    parser.add_argument("--days", type=int, default=0)
    args = parser.parse_args()
    try:
        result = fetch(args.config, args.account, args.query, args.max, args.days)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
