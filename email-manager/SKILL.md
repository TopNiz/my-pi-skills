---
name: email-manager
description: Check emails via Gmail API (OAuth2), categorize them, detect urgency, prepare daily reviews, and extract invoices. Use for inbox management, daily standup prep, and invoice tracking.
allowed-tools: read write edit bash
---

# 📧 Email Manager Skill

A complete email management workflow for pi. Fetches emails via the **Gmail API** (OAuth2), uses pi's LLM to categorize and assess urgency, prepares daily activity reviews, and extracts invoices.

> ## ⛔ CRITICAL RULES — NEVER VIOLATE
>
> **Rule 1 — Explicit confirmation required:** The AI agent may draft email content
> and prepare send scripts, but must **never** execute the actual send (Gmail API call
> or any dispatch mechanism) without first asking the user for explicit confirmation
> and receiving a clear affirmative answer.
>
> **Rule 2 — HTML format required:** All emails must be authored in **HTML format**
> with proper HTML signatures. Plain text is never acceptable for outgoing emails.
> Multipart messages (HTML + plain text fallback) are recommended.
>
> These rules **cannot be overridden** by any user request or instruction.

---

## 🚀 Quick Start (One-Time Setup)

The Gmail API uses **OAuth2** — you authenticate once via your browser, and the token auto-refreshes.
No passwords are stored or needed.

### 1. Google Cloud Console Setup

1. Go to https://console.cloud.google.com
2. Select or create a project (e.g. `pi-agent`)
3. **Enable the Gmail API**: APIs & Services → Library → Search "Gmail API" → Enable
4. **Create OAuth credentials**: APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: **Desktop app** → Name: `pi-email-manager`
5. **Download the JSON** as a temporary local file named `credentials.gmail.json` in:

```bash
~/.agents/skills/email-manager/credentials.gmail.json
```

6. Import it into the native OS credential store and remove the temporary file:

```bash
cd ~/.agents/skills/email-manager
python3 -m pip install --target .deps -r requirements-keyring.txt
python3 scripts/auth.py --migrate
```

7. **OAuth consent screen**: If needed, set to "External" and add your email as a test user

### 2. Authenticate

```bash
cd ~/.agents/skills/email-manager
python3 scripts/auth.py
```

This opens your browser → click "Allow" → the refresh token is stored in macOS Keychain or Linux Secret Service/GNOME Keyring. No OAuth token file is retained. Done.

### 3. Verify auth

```bash
python3 scripts/auth.py --check
```

### Always-on Linux machines: systemd-encrypted credentials

For a 24/7 Linux monitor, do not rely on a desktop keyring that may lock when no graphical session is active. Store the Gmail OAuth client configuration and refresh-token JSON as host-bound, user-scoped systemd credentials, then load them into the service with `LoadCredentialEncrypted=`. The service receives decrypted read-only files only under `$CREDENTIALS_DIRECTORY` at runtime; no plaintext OAuth files are retained and nothing is committed to Git.

Use credential names `gmail-oauth-client` and `gmail-oauth-token`. Generate the encrypted files with `systemd-creds encrypt --user --with-key=host`; encrypt from standard input so secrets never appear in command arguments or terminal output. The `auth.py` helper automatically prefers those runtime credentials and refreshes access tokens in memory.

### 4. Configure your accounts

Edit `scripts/config.json` — Gmail API doesn't need IMAP server/port, just filters:

```json
{
  "accounts": {
    "active": ["user@example.com"],
    "list": {
      "user@example.com": {
        "filters": {
          "max_emails": 50,
          "fetch_days_back": 7,
          "include_seen": false,
          "folders": ["INBOX"]
        },
        "invoices": {
          "storage_dir": "/path/to/invoices",
          "auto_extract": true,
          "save_attachments": true
        },
        "protected_senders": {
          "list": ["noreply@newsletter.com"]
        },
        "routing": {
          "rules": []
        }
      }
    }
  }
}
```

**No passwords in config.json** — OAuth2 handles everything.

### 5. Customize categories (optional)

Edit `references/CATEGORIES.md` to add/remove categories that match your workflow.

---

## 📬 Core Workflow: Check & Categorize Emails

### Step 1 — Fetch Emails

Run the fetch script (now uses Gmail API):

```bash
cd ~/.agents/skills/email-manager
python3 scripts/fetch_emails.py scripts/config.json
```

Options:
```bash
# Go back more days
python3 scripts/fetch_emails.py scripts/config.json --days=14

# Include already-seen emails
python3 scripts/fetch_emails.py scripts/config.json --days=1   # sets include_seen=true via fetch_days_back=1

# Custom Gmail search query (overrides date/folder filters)
python3 scripts/fetch_emails.py scripts/config.json --search="from:example.com after:2026/05/01"

# Fetch from a specific label
python3 scripts/fetch_emails.py scripts/config.json --folder=INBOX

# Limit results
python3 scripts/fetch_emails.py scripts/config.json --max=10
```

Save the output to a temp file for processing:

```bash
python3 scripts/fetch_emails.py scripts/config.json > /tmp/emails.json
```

### Step 2 — Categorize with pi's LLM

Read the fetched emails and categorize each one. Use the taxonomy from `references/CATEGORIES.md`.

**Categorization guidelines:**

For each email, determine:
1. **Primary category** — from the taxonomy in `references/CATEGORIES.md`
2. **Tags** — relevant tags from the taxonomy
3. **Urgency level**:
   - `🔴 URGENT` — Requires action today (deadline, overdue, critical security alert)
   - `🟡 Follow-up` — Needs response within 48 hours
   - `🔵 Informational` — Read only, no action needed
   - `⚪ Archive` — Can be filed away
4. **Summary** — 1-line what this email is about

**Present a categorized overview** using this format:

```
┌─────────────────────────────────────────────────────┐
│ 📧 Email Inbox — Categorized Summary               │
│ Account: user@email.com                             │
│ Fetched: 2026-05-14T09:00:00                        │
│ Total: 12 unread                                    │
└─────────────────────────────────────────────────────┘

🔴 URGENT (2)
  • [subject] — from sender — deadline/summary
  • [subject] — from sender — deadline/summary

🟡 Follow-up (3)
  • [subject] — from sender — category

🔵 Informational (5)
  • [subject] — from sender — category

⚪ Archive (2)
  • [subject] — from sender

📊 Categories Breakdown:
  invoice: 3  |  client: 2  |  security: 1  |  system: 1  |  social: 3  |  personal: 2
```

### Step 3 — User Interaction

After presenting the categorized summary, offer to:
- **Read full email** — User says "read the one about X" → show full body_text
- **Reply draft** — User says "draft a reply to X" → prepare a response (see [Reply drafting](#-reply-drafting) below)
- **Flag for action** — User says "flag this" → mark email in your task list
- **Extract invoices** — See invoice workflow below

---

### ✍️ Reply Drafting

When the user asks to draft a reply, use the **[reply-style](../reply-style/SKILL.md)** skill to generate the email content:

1. **Load the reply-style skill** — Read `../reply-style/SKILL.md` and `../reply-style/references/STYLE-GUIDE.md`
2. **Look up the sender** — Check if the sender exists in `../reply-style/contacts/index.json`
3. **Read contact history** — If found, read their messages from `../reply-style/contacts/messages/<email>.json` to match your authoring style
4. **Apply presentation templates** — For structured data (invoices, readings, amounts), use `../reply-style/references/EMAIL-TEMPLATES.md` for the HTML layout (tables, headings, colors)
5. **Use the correct signature** — French or English HTML signature from `STYLE-GUIDE.md` section 11, populated from `../reply-style/config/signature.json`
6. **Save as draft in Gmail** — Use the Gmail API `drafts.create()` with `multipart/alternative` (HTML + plain text)
7. **Wait for confirmation** — Never send without explicit user approval

> The reply-style skill handles **authoring style** (tone, greeting, language) and **presentation style** (HTML tables, layout, signature). The email-manager skill handles Gmail API transport (fetching, drafting, sending).

---

## 📋 Daily Activity Review

Use this workflow for daily standup or end-of-day review:

```bash
python3 scripts/fetch_emails.py scripts/config.json --days=1 --include-seen > /tmp/today.json
```

Then process the JSON and present a **Daily Review** in this format:

```
┌─────────────────────────────────────────────────────┐
│ 📋 Daily Review — 2026-05-14                       │
│ Account: user@email.com                             │
└─────────────────────────────────────────────────────┘

📥 RECEIVED TODAY (15 emails)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📧 Account 1: user@example.com (8 emails)

🔴 Priority Items:
  1. [Subject] — [Sender]
     → Why it matters, what action is needed
  ...

📧 Account 2: other@domain.com (7 emails)

🔴 Priority Items:
  1. [Subject] — [Sender]
     → Why it matters, what action is needed
  ...

📊 Summary: 2 urgent items, 3 follow-ups needed, 5 informational, 2 to archive
```

Ask after presenting: "Shall I archive processed items, or prepare any replies?"

---

## 💰 Invoice Extraction Workflow

### Step 1 — Find invoices in fetched emails

```bash
cd ~/.agents/skills/email-manager
python3 scripts/fetch_emails.py scripts/config.json > /tmp/emails.json
python3 scripts/extract_invoices.py /tmp/emails.json scripts/config.json
```

The script outputs a JSON report and saves an invoice index to the storage directory.

### Step 2 — Present invoice findings

Show the user what was found:

```
┌─────────────────────────────────────────────────────┐
│ 💰 Invoice Detector                                 │
│ Scanned: 45 emails                                  │
│ Found: 3 potential invoices                         │
└─────────────────────────────────────────────────────┘

📄 1. INVOICE-2026-05-14 — ACME Corp
   From: billing@acme.com
   Amount: €1,250.00 (estimated)
   Files: invoice_2026-05.pdf (142KB)
   → Save to: /path/to/Invoices/2026-05-14_ACME_invoice_2026-05.pdf

📄 2. Payment Confirmation — Stripe
   From: noreply@stripe.com
   Amount: €49.99
   → Informational, no attachment

📄 3. SaaS Renewal — GitHub
   From: billing@github.com
   Amount: €12.00/month
   → Subscription, review before next billing
```

### Step 3 — Download & store invoice attachments

For confirmed invoices with attachments, download them via the Gmail API:

```python
# The email JSON contains the message ID (uid) and thread_id.
# Use the Gmail API to download attachments:
message = service.users().messages().get(userId='me', id=msg_id).execute()
for part in message['payload']['parts']:
    if part['filename']:
        att_id = part['body']['attachmentId']
        att = service.users().messages().attachments().get(
            userId='me', messageId=msg_id, id=att_id
        ).execute()
        data = base64.urlsafe_b64decode(att['data'])
        # Save to storage_dir/filename
```

### Step 4 — Update invoice index

After downloading, update the invoice index in the storage directory:

```bash
# Re-run the extract script to refresh the index
python3 scripts/extract_invoices.py /tmp/emails.json scripts/config.json
```

The index file `_invoice_index_YYYYMMDD_HHMMSS.json` is saved in the storage directory.

---

## 📁 Automatic Email Routing

The `config.json` file has a `routing` section that defines where emails should be moved when they arrive:

```json
"routing": {
  "rules": [
    {"sender": "invoices@provider.com", "label": "Finance/Invoices"},
    {"sender": "*@cloud-host.com", "label": "IT/Cloud"},
    {"sender": "no-reply@tickets.vendor.com", "label": "Finance/Invoices"},
    {"sender": "support@cloud-host.net", "filter": "subject:invoice", "label": "Finance/Invoices"}
  ]
}
```

You can use:
- **Exact sender**: `user@domain.com`
- **Domain wildcard**: `*@domain.com` matches all senders from that domain
- **Filter**: optional subject filter for finer control

### Applying Routing via Gmail API

When checking emails, apply routing rules to new unseen emails and offer to move them. Always confirm with the user before bulk-moving.

**Moving an email to a label (Gmail API):**

```python
# Add label, remove INBOX label
service.users().messages().modify(
    userId='me',
    id=msg_id,
    body={
        'addLabelIds': ['Label_123'],  # label ID (not name)
        'removeLabelIds': ['INBOX']
    }
).execute()
```

> **Note:** Gmail labels use internal IDs (like `Label_123`). To find a label ID from its name:
> ```python
> labels = service.users().labels().list(userId='me').execute()
> label_id = [l['id'] for l in labels['labels'] if l['name'] == 'Finance/Invoices'][0]
> ```

### Protecting Senders

Update `scripts/config.json` whenever the user says "keep" or "don't delete".
Find the account in `accounts.list.<email>.protected_senders`:

```json
{
  "accounts": {
    "list": {
      "user@example.com": {
        "protected_senders": {
          "list": [
            "noreply@newsletter.com",
            "no-reply@tickets.vendor.com",
            "invoices@provider.com"
          ]
        },
        "routing": {
          "rules": [
            {"sender": "invoices@provider.com", "label": "Finance/Invoices"}
          ]
        }
      }
    }
  }
}
```

---

## 🧹 Bulk Cleanup — Exact Step-by-Step Process

Follow these exact steps in order when the user asks to clean up emails from a sender.

### Step 1: Find the sender's actual email address

Search the fetched JSON for sender addresses, or use the Gmail API directly:

```python
service = get_service()
response = service.users().messages().list(
    userId='me',
    q='from:domain.com',
    maxResults=500
).execute()
message_ids = [m['id'] for m in response.get('messages', [])]
```

### Step 2: Show sample subjects to the user

Always show the last 10-15 subjects so the user can decide what to do.

```python
for msg_id in message_ids[-15:]:
    msg = service.users().messages().get(
        userId='me', id=msg_id, format='metadata',
        metadataHeaders=['Subject', 'Date']
    ).execute()
    headers = msg['payload']['headers']
    subject = next(h['value'] for h in headers if h['name'] == 'Subject')
    date = next(h['value'] for h in headers if h['name'] == 'Date')
    print(f"{date} | {subject}")
```

### Step 3: Check `protected_senders` in config.json

Before ANY delete/unsubscribe, read `scripts/config.json` and check if the sender is in `protected_senders.list`. If yes:
- ❌ Never delete
- ❌ Never unsubscribe
- ✅ Only move folders if asked

### Step 4: Choose the action pattern

| User says | Action |
|-----------|--------|
| "Supprimer" | Bulk trash via Gmail API (`modify` with `TRASH` label or `trash()`) |
| "Désabonner + supprimer" | Find unsubscribe link → curl → bulk trash |
| "Supprimer les vieux de +2 mois" | Filter by date, bulk trash only those |
| "Déplacer vers dossier" | `modify()` → add label + remove INBOX |

### Step 5: Unsubscribe (if needed)

Use the `find_unsub.py` script:

```bash
python3 ~/.agents/skills/email-manager/tmp/find_unsub.py sender@example.com
```

The script reads one email, extracts the `List-Unsubscribe` header, and prints URLs.

If you find a URL, use `curl -s -L <url> -o /dev/null -w "HTTP %{http_code}\n"`.

**Edge cases:**
- If the link has `id=undefined` → try the link from an OLDER email which may have a valid ID
- If only a `mailto:` link → unsubscribe not possible via HTTP, just delete
- If no unsubscribe header at all → just delete

### Step 6: Bulk delete via Gmail API

**Gmail API has rate limits (250 quota units/user/sec). Each `modify` costs 5 units.**
Batch operations are essential for bulk deletes.

```python
from googleapiclient.http import BatchHttpRequest

def trash_callback(request_id, response, exception):
    if exception:
        print(f"Error trashing {request_id}: {exception}")

batch = service.new_batch_http_request(callback=trash_callback)
for msg_id in message_ids:
    batch.add(service.users().messages().trash(userId='me', id=msg_id))
batch.execute()
print(f"Trashed {len(message_ids)} messages")
```

For simpler cases, use the `modify` method to add the `TRASH` label:

```python
for msg_id in message_ids:
    service.users().messages().modify(
        userId='me', id=msg_id,
        body={'addLabelIds': ['TRASH'], 'removeLabelIds': ['INBOX']}
    ).execute()
```

### Step 7: Bulk move to label (Gmail API)

```python
# First, find the target label ID
labels = service.users().labels().list(userId='me').execute()
target_label_id = next(
    l['id'] for l in labels['labels']
    if l['name'] == 'Finance/Invoices'
)

for msg_id in message_ids:
    service.users().messages().modify(
        userId='me', id=msg_id,
        body={
            'addLabelIds': [target_label_id],
            'removeLabelIds': ['INBOX']
        }
    ).execute()
```

### Step 8: Delete by age (older than N months)

Use Gmail's search query to filter by date:

```python
cutoff = (datetime.now() - timedelta(days=60)).strftime('%Y/%m/%d')
response = service.users().messages().list(
    userId='me',
    q=f'from:domain.com before:{cutoff}',
    maxResults=500
).execute()
```

### Step 9: Always verify

After any operation, re-search and confirm 0 remaining in INBOX:

```python
response = service.users().messages().list(
    userId='me',
    q='from:sender@example.com in:inbox'
).execute()
remaining = len(response.get('messages', []))
print(f'Reste INBOX: {remaining}')
```

---

### Pitfalls to Avoid

- ❌ **Don't loop API calls one-by-one for hundreds of messages** — use batch requests
- ❌ **Don't use `datetime.strptime` for email dates** — always use `parsedate_to_datetime`
- ❌ **Don't unsubscribe if sender is in `protected_senders`**
- ❌ **Don't use IMAP-specific folder names with Gmail API** — Gmail uses label IDs, not folder paths
- ❌ **Don't store OAuth tokens in config files or token files** — use the native credential store

---

## 🔐 Security Notes

- **OAuth2** — No passwords stored. Authentication is via Google's OAuth2 flow.
- **Native credential store** — OAuth client configuration and refresh tokens are stored in macOS Keychain or Linux Secret Service/GNOME Keyring, never committed or printed.
- **Temporary migration files** — `credentials.gmail.json` and `token.gmail.json` are imported with `auth.py --migrate` and removed only after successful native-store writes.
- **Revoke access** at https://myaccount.google.com/permissions anytime.
- **Invoice storage**: Ensure the invoice directory has appropriate backups.
- **Scope**: `gmail.modify` — required for reading, deleting, and moving emails.

## 📂 Skill Files Reference

```
email-manager/
├── SKILL.md                    ← This file — skill instructions
├── requirements-keyring.txt    ← Native credential-store dependency
├── scripts/
│   ├── config.json             ← Account config (no passwords!)
│   ├── auth.py                 ← Gmail OAuth2 via the native credential store
│   ├── fetch_emails.py         ← Gmail API email fetcher → JSON
│   ├── extract_invoices.py     ← Invoice detection & metadata
│   └── setup.sh                ← One-time interactive setup (legacy)
├── references/
│   ├── CATEGORIES.md           ← Category taxonomy (edit to customize)
│   └── user_preferences.json   ← Learned categorization rules (auto-created)
```

## 🔑 Gmail API vs IMAP — Key Differences

| Action | Old (IMAP) | New (Gmail API) |
|--------|-----------|----------------|
| Auth | App Password in Keychain | OAuth2 (browser consent) |
| Search query | `FROM x SINCE y` | `from:x after:y` |
| Folders | IMAP folders | Gmail labels |
| Delete | `STORE +FLAGS (\Deleted)` → expunge | `messages().trash()` or `modify()` with `TRASH` label |
| Move | `COPY` → `STORE +FLAGS (\Deleted)` → expunge | `messages().modify()` → add/remove labelIds |
| Attachments | Inline in IMAP fetch | `messages().get()` with `format=full` |
| Rate limits | ~1500 connections/day | 250 quota units/user/sec (generous) |
| Auth storage | macOS Keychain | Native credential store (OAuth2) |

> **Note:** The `_gmail_labels` and `thread_id` fields are added to each email in the JSON output for use in Gmail API operations (delete, move, etc.).
