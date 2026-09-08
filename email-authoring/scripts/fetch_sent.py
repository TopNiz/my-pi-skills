#!/usr/bin/env python3
"""
Fetch sent emails from IMAP and build per-contact message databases.

Usage:
    python3 fetch_sent.py config.json

Output:
    - contacts/index.json : master contact list
    - contacts/messages/<email>.json : messages per contact
"""

import imaplib
import email
import json
import os
import re
import sys
import subprocess
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime
from collections import defaultdict

# ─── Helpers ────────────────────────────────────────────────────────────────

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
        print(f"   Add it: security add-generic-password -a \"{email_addr}\" -s \"{service}\" -w \"YOUR_PASSWORD\" -U")
        sys.exit(1)


def decode_mime_header(value):
    """Decode a MIME-encoded header value."""
    if not value:
        return ""
    decoded_parts = decode_header(value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            try:
                result.append(part.decode(charset or "utf-8", errors="replace"))
            except LookupError:
                result.append(part.decode("utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def extract_email_address(header_value):
    """Extract a clean email address from a From/To header."""
    if not header_value:
        return None, None
    decoded = decode_mime_header(header_value)
    # Match pattern like "Name <email>" or just "email"
    match = re.search(r'<([^>]+)>', decoded)
    if match:
        email_addr = match.group(1).strip().lower()
        name = decoded.split('<')[0].strip().strip('"').strip("'")
        return email_addr, name or None
    # Plain email address
    if '@' in decoded:
        return decoded.strip().lower(), None
    return None, None


def clean_body(msg):
    """Extract plain text body from an email message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body += payload.decode(charset, errors="replace")
                except Exception:
                    pass
            elif content_type == "text/html" and not body and "attachment" not in content_disposition:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body += payload.decode(charset, errors="replace")
                except Exception:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="replace")
        except Exception:
            pass
    return body.strip()


def try_sent_folders(mail, candidates):
    """Try to select the Sent folder from a list of candidates."""
    for folder in candidates:
        try:
            status, _ = mail.select(f'"{folder}"')
            if status == 'OK':
                print(f"  ✅ Selected Sent folder: {folder}")
                return folder
        except imaplib.IMAP4.error:
            continue
    return None


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 fetch_sent.py config.json")
        sys.exit(1)

    config_path = sys.argv[1]
    config_dir = os.path.dirname(os.path.abspath(config_path))

    with open(config_path) as f:
        config = json.load(f)

    contacts_dir = os.path.abspath(os.path.join(config_dir, config.get("contacts_dir", "../contacts")))
    messages_dir = os.path.join(contacts_dir, "messages")
    os.makedirs(messages_dir, exist_ok=True)

    pw_config = config.get("password_source", {})
    keychain_service = pw_config.get("service", "email-manager")
    accounts_cfg = config.get("accounts", {})
    active_accounts = accounts_cfg.get("active", [])

    if not active_accounts:
        print("❌ No active accounts configured.")
        sys.exit(1)

    # Try common Sent folder names for auto-detection
    common_sent_folders = [
        '[Gmail]/Sent Mail',
        '[Google Mail]/Sent Mail',
        'Sent',
        'Sent Items',
        'Sent Messages',
        'INBOX.Sent',
        'INBOX/Sent',
    ]

    contacts_data = {}  # email -> {name, category, language, messages[]}

    for account_email in active_accounts:
        acct = accounts_cfg["list"].get(account_email, {})
        imap_cfg = acct.get("imap", {})
        sent_folder_cfg = acct.get("sent_folder")
        months_back = acct.get("months_back", 6)

        server = imap_cfg.get("server", "imap.gmail.com")
        port = imap_cfg.get("port", 993)
        username = imap_cfg.get("username", account_email)

        print(f"\n📧 Account: {account_email}")
        print(f"   Server: {server}:{port}")

        password = get_password(account_email, keychain_service)

        # Connect
        print("   Connecting...")
        mail = imaplib.IMAP4_SSL(server, port)
        mail.login(username, password)
        print("   ✅ Logged in")

        # Find Sent folder
        if sent_folder_cfg:
            status, _ = mail.select(f'"{sent_folder_cfg}"')
            if status == 'OK':
                print(f"  ✅ Selected Sent folder: {sent_folder_cfg}")
            else:
                print(f"  ⚠️  Configured Sent folder '{sent_folder_cfg}' not found, trying auto-detect...")
                sent_folder_cfg = try_sent_folders(mail, common_sent_folders)
                if not sent_folder_cfg:
                    print("  ❌ Could not find Sent folder. Aborting.")
                    mail.logout()
                    continue
        else:
            sent_folder_cfg = try_sent_folders(mail, common_sent_folders)
            if not sent_folder_cfg:
                print("  ❌ Could not find Sent folder. Aborting.")
                mail.logout()
                continue

        # Search for sent messages in the last N months
        since_date = (datetime.now(timezone.utc) - timedelta(days=30 * months_back)).strftime("%d-%b-%Y")
        print(f"   Searching sent messages since {since_date}...")

        search_cmd = f'SINCE {since_date}'
        status, data = mail.uid('SEARCH', None, search_cmd)

        if status != 'OK' or not data[0]:
            print("   No sent messages found in this period.")
            mail.logout()
            continue

        uids = data[0].split()
        total = len(uids)
        print(f"   Found {total} sent messages")
        print(f"   Fetching message details...")

        messages_for_contact = defaultdict(list)

        # Process in chunks to avoid memory issues
        chunk_size = 100
        for chunk_start in range(0, total, chunk_size):
            chunk = uids[chunk_start:chunk_start + chunk_size]
            uid_str = ','.join(uid.decode() if isinstance(uid, bytes) else uid for uid in chunk)

            status, msg_data = mail.uid('FETCH', uid_str, '(BODY.PEEK[HEADER.FIELDS (TO SUBJECT DATE)])')
            if status != 'OK':
                continue

            for i in range(0, len(msg_data), 2):
                raw_data = msg_data[i]
                if not isinstance(raw_data, tuple):
                    continue

                raw_email = raw_data[1]
                msg = email.message_from_bytes(raw_email)

                to_header = msg.get('To', '')
                subject = decode_mime_header(msg.get('Subject', '(No subject)'))
                date_str = msg.get('Date', '')

                # Parse date
                msg_date = None
                try:
                    msg_date = parsedate_to_datetime(date_str)
                except Exception:
                    pass

                # Extract TO recipient(s)
                recipients = []
                for addr in email.utils.getaddresses([to_header]):
                    email_addr = addr[1].strip().lower() if len(addr) > 1 else None
                    name = addr[0].strip().strip('"') if addr and addr[0] else None
                    if email_addr and '@' in email_addr:
                        # Skip self (BCC copies etc.)
                        if email_addr != account_email.lower():
                            # Also strip any display names that might be emails
                            clean_name = None
                            if name and '@' not in name and len(name) > 1:
                                clean_name = name
                            recipients.append({
                                'email': email_addr,
                                'name': clean_name
                            })

                if not recipients:
                    continue

                for recip in recipients:
                    messages_for_contact[recip['email']].append({
                        'date': msg_date.isoformat() if msg_date else date_str,
                        'subject': subject,
                        'to_email': recip['email'],
                        'to_name': recip['name'],
                    })

            # Progress
            pct = min(100, int((chunk_start + chunk_size) / total * 100))
            print(f"   Progress: {pct}% ({min(chunk_start + chunk_size, total)}/{total})", end='\r')

        print(f"\n   ✅ Found messages for {len(messages_for_contact)} unique recipients")

        # Now fetch full message bodies for a sample (last 20 messages per contact max)
        print("   Fetching message bodies (up to 20 per contact)...")
        for contact_email in list(messages_for_contact.keys())[:50]:  # Limit to 50 contacts
            msgs = messages_for_contact[contact_email]
            # Only fetch bodies for the most recent messages (max 20)
            recent_msgs = sorted(msgs, key=lambda m: m.get('date', ''), reverse=True)[:20]

            # Build a search for these specific messages
            # We need to fetch full messages by UID... actually this is complex.
            # Better approach: re-fetch the Sent folder and match by date+subject
            # For now, let's try a different approach - fetch full bodies by UID range

        # ── Alternative: simpler approach ──
        # Since we already have UIDs from the search, let's re-fetch them in chunks
        # and extract bodies for ALL contacts at once

        print("   Fetching full messages with bodies...")
        messages_by_uid = {}  # uid -> {to, subject, date, body}

        for chunk_start in range(0, total, chunk_size):
            chunk = uids[chunk_start:chunk_start + chunk_size]
            uid_str = ','.join(uid.decode() if isinstance(uid, bytes) else uid for uid in chunk)

            status, msg_data = mail.uid('FETCH', uid_str, '(BODY.PEEK[])')
            if status != 'OK':
                continue

            for i in range(0, len(msg_data), 2):
                raw_data = msg_data[i]
                if not isinstance(raw_data, tuple):
                    continue

                raw_bytes = raw_data[1]
                msg = email.message_from_bytes(raw_bytes)

                to_header = msg.get('To', '')
                subject = decode_mime_header(msg.get('Subject', '(No subject)'))
                date_str = msg.get('Date', '')
                body = clean_body(msg)

                # Parse date
                msg_date = None
                try:
                    msg_date = parsedate_to_datetime(date_str)
                except Exception:
                    pass

                # Extract TO recipients
                recipients = []
                for addr in email.utils.getaddresses([to_header]):
                    email_addr = addr[1].strip().lower() if len(addr) > 1 else None
                    name = addr[0].strip().strip('"') if addr and addr[0] else None
                    if email_addr and '@' in email_addr and email_addr != account_email.lower():
                        clean_name = None
                        if name and '@' not in name and len(name) > 1:
                            clean_name = name
                        recipients.append({
                            'email': email_addr,
                            'name': clean_name
                        })

                if not recipients or not body:
                    continue

                for recip in recipients:
                    key = recip['email']
                    if key not in contacts_data:
                        contacts_data[key] = {
                            'email': key,
                            'name': recip['name'],
                            'category': 'unknown',
                            'language': 'unknown',
                            'messages': []
                        }
                    elif not contacts_data[key]['name'] and recip['name']:
                        contacts_data[key]['name'] = recip['name']

                    contacts_data[key]['messages'].append({
                        'date': msg_date.isoformat() if msg_date else date_str,
                        'subject': subject,
                        'body': body[:2000],  # Truncate very long bodies
                    })

            pct = min(100, int((chunk_start + chunk_size) / total * 100))
            print(f"   Bodies: {pct}% ({min(chunk_start + chunk_size, total)}/{total})", end='\r')

        print(f"\n   ✅ Extracted bodies for {len(contacts_data)} contacts")

        mail.logout()
        print("   📤 Logged out")

    # ── Save contact files ──────────────────────────────────────────────
    print(f"\n💾 Saving contact files...")
    index = {}
    for email_addr, contact in contacts_data.items():
        # Sort messages by date (newest first)
        contact['messages'].sort(key=lambda m: m.get('date', ''), reverse=True)
        # Keep recent messages only (max 50 per contact)
        if len(contact['messages']) > 50:
            contact['messages'] = contact['messages'][:50]

        safe_email = email_addr.replace('@', '_at_').replace('.', '_dot_')
        filepath = os.path.join(messages_dir, f"{safe_email}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(contact, f, ensure_ascii=False, indent=2)

        index[email_addr] = {
            'name': contact['name'],
            'category': contact['category'],
            'language': contact['language'],
            'message_count': len(contact['messages']),
            'file': f"{safe_email}.json"
        }

    # Save index
    index_path = os.path.join(contacts_dir, "index.json")
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Done! Processed {len(contacts_data)} contacts")
    print(f"   Index: {index_path}")
    print(f"   Messages: {messages_dir}/")

    # Show summary
    print(f"\n📊 Summary:")
    categories = defaultdict(int)
    total_msgs = 0
    for email_addr, info in index.items():
        categories[info['category']] += 1
        total_msgs += info['message_count']
    print(f"   Total contacts: {len(index)}")
    print(f"   Total messages: {total_msgs}")
    for cat, count in sorted(categories.items()):
        print(f"   - {cat}: {count} contacts")


if __name__ == "__main__":
    main()
