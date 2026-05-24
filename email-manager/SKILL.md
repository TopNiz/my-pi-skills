---
name: email-manager
description: Check emails via IMAP, categorize them, detect urgency, prepare daily reviews, and extract invoices. Supports Gmail and any IMAP-enabled email provider. Use for inbox management, daily standup prep, and invoice tracking.
allowed-tools: read write edit bash
---

# 📧 Email Manager Skill

A complete email management workflow for pi. Fetches emails via IMAP, uses pi's LLM to categorize and assess urgency, prepares daily activity reviews, and extracts invoices.

---

## 🚀 Quick Start (One-Time Setup)

### 1. Configure your email account

Run the setup script:

```bash
cd ~/.agents/skills/email-manager
chmod +x scripts/setup.sh
./scripts/setup.sh
```

This prompts for:
- **IMAP server** (default: `imap.gmail.com` — works for Gmail, Google Workspace)
- **Port** (default: `993`)
- **Email address**
- **Password / App Password** (for Gmail with 2FA, create an App Password at https://myaccount.google.com/apppasswords)
- **Invoice storage directory**

### 2. Or configure manually

Edit `scripts/config.json` with your IMAP credentials:

```json
{
  "imap": {
    "server": "imap.gmail.com",
    "port": 993,
    "use_ssl": true,
    "username": "your.email@gmail.com",
    "password": "your-app-password"
  },
  "filters": {
    "max_emails": 50,
    "fetch_days_back": 7,
    "include_seen": false,
    "folders": ["INBOX"]
  },
  "invoices": {
    "storage_dir": "/path/to/invoice/storage",
    "auto_extract": true,
    "save_attachments": true
  }
}
```

### 3. Customize categories (optional)

Edit `references/CATEGORIES.md` to add/remove categories that match your workflow.

---

## 📬 Core Workflow: Check & Categorize Emails

### Step 1 — Fetch Emails

Run the fetch script to get recent unseen emails as structured JSON:

```bash
cd ~/.agents/skills/email-manager
python3 scripts/fetch_emails.py scripts/config.json
```

Options:
```bash
# Fetch from a specific folder
python3 scripts/fetch_emails.py scripts/config.json --folder=INBOX

# Go back more days
python3 scripts/fetch_emails.py scripts/config.json --days=14

# Include already-seen emails
python3 scripts/fetch_emails.py scripts/config.json --days=1   # sets include_seen=true, so today's seen emails come back

# Custom IMAP search
python3 scripts/fetch_emails.py scripts/config.json --search="FROM example.com SINCE 1-May-2026"

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
- **Reply draft** — User says "draft a reply to X" → prepare a response
- **Flag for action** — User says "flag this" → mark email in your task list
- **Extract invoices** — See invoice workflow below

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

🔴 Priority Items:
  1. [Subject] — [Sender]
     → Why it matters, what action is needed
  2. [Subject] — [Sender]
     → Why it matters, what action is needed

📁 By Category:
  • Invoices/Finance: 3 (2 new invoices, 1 payment confirmation)
  • Clients: 2 (1 project update, 1 new inquiry)
  • Operations: 4 (2 deployments, 1 security alert, 1 system notice)
  • Personal/Other: 6 (3 newsletters, 2 social, 1 personal)

💰 Invoices Detected:
  • [Vendor Name] — €XXX.XX — due date — status
  • [Vendor Name] — €XXX.XX — due date — status

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

For confirmed invoices with attachments, use the fetch script with attachment downloading:

```bash
# The script outputs which emails contain invoices.
# For each invoice email, extract the attachment via IMAP.
# The attachments are referenced by UID. Use a targeted fetch:
python3 scripts/fetch_emails.py scripts/config.json \
  --search="UID <uid1> <uid2>" > /tmp/invoice_emails.json
```

Alternatively, manually download attachments by:
1. Reading the email body from the JSON to find download links
2. Saving PDFs referenced in the email to the configured storage directory

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
    {"sender": "invoices@provider.com", "folder": "Finance/Invoices"},
    {"sender": "*@cloud-host.com", "folder": "IT/Cloud"},
    {"sender": "no-reply@tickets.vendor.com", "folder": "Finance/Invoices"},
    {"sender": "support@cloud-host.net", "filter": "subject:invoice", "folder": "Finance/Invoices"}
  ]
}
```

You can use:
- **Exact sender**: `user@domain.com`
- **Domain wildcard**: `*@domain.com` matches all senders from that domain
- **Filter**: optional subject filter for finer control

### Applying Routing

When checking emails, the agent should apply routing rules to new unseen emails and offer to move them. Always confirm with the user before bulk-moving.

---

## 🧠 Training Categories (Interactive Learning)

The user can teach the skill their preferred categories. When the user says something like:

> "This email should be categorized as X, not Y"

1. Save the example to a learning file:

```bash
cat >> ~/.agents/skills/email-manager/references/user_preferences.json << 'EOF'
{
  "learned_rules": [
    {
      "pattern": "newsletter@example.com",
      "category": "social",
      "tag": "unsubscribe"
    }
  ]
}
```

2. Update future categorization to follow these rules.

---

## 🧹 Bulk Cleanup — Exact Step-by-Step Process

Follow these exact steps in order when the user asks to clean up emails from a sender.

### Step 1: Find the sender's actual email address

Search by domain or known address. Some senders have MIME-encoded names without an email in the FROM field — check `Reply-To` or `Return-Path` headers.

```python
s, d = mail.uid('SEARCH', None, 'FROM', 'domain.com')
# or scan last 500 UIDs for a name pattern
```

### Step 2: Show sample subjects to the user

Always show the last 10-15 subjects so the user can decide what to do.

```python
for uid in uids[-15:]:
    s2, d2 = mail.uid('FETCH', uid, '(BODY.PEEK[HEADER.FIELDS (SUBJECT DATE)])')
    # decode + print subject and date
```

### Step 3: Check `protected_senders` in config.json

Before ANY delete/unsubscribe, read `scripts/config.json` and check if the sender is in `protected_senders.list`. If yes:
- ❌ Never delete
- ❌ Never unsubscribe
- ✅ Only move folders if asked

### Step 4: Choose the action pattern

Choose one based on user's instructions:

| User says | Action |
|-----------|--------|
| "Supprimer" | Bulk STORE +FLAGS (\Deleted) + expunge |
| "Désabonner + supprimer" | Find unsubscribe link → curl → bulk delete |
| "Supprimer les vieux de +2 mois" | Parse dates with `parsedate_to_datetime()`, filter old UIDs, bulk delete only those |
| "Déplacer vers dossier" | COPY to folder + STORE +FLAGS (\Deleted) in batches of 50 |

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

### Step 6: Bulk delete (fast method)

**Critical: always use comma-separated UIDs in a single STORE command.**

```python
# Fast — hundreds of emails in 1-2 seconds
uid_str = ','.join(u.decode() for u in uids)
mail.uid('STORE', uid_str, '+FLAGS', r'(\Deleted)')
mail.expunge()
```

For very large batches (>500 UIDs), split into chunks of 200:

```python
for i in range(0, len(uids), 200):
    chunk = uids[i:i+200]
    mail.uid('STORE', ','.join(u.decode() for u in chunk), '+FLAGS', r'(\Deleted)')
mail.expunge()
```

### Step 7: Bulk move to folder (slower, needs COPY)

COPY requires individual or batched operations. Use chunks of 50:

```python
for i in range(0, len(uids), 50):
    chunk = uids[i:i+50]
    uid_str = ','.join(u.decode() for u in chunk)
    mail.uid('COPY', uid_str, '"Target/Folder"')
    mail.uid('STORE', uid_str, '+FLAGS', r'(\Deleted)')
mail.expunge()
```

### Step 8: Delete by age (older than N months)

Parse the Date header correctly:

```python
from email.utils import parsedate_to_datetime

for line in raw.split('\r\n'):
    if line.lower().startswith('date:'):
        date_dt = parsedate_to_datetime(line[5:].strip())
        # Now compare with cutoff
```

**NEVER use** `datetime.strptime()` with a fixed format — email date formats vary.

### Step 9: Always verify

After any operation, re-search the sender and confirm 0 remaining in INBOX:

```python
s, d = mail.uid('SEARCH', None, 'FROM', 'sender@example.com')
remaining = len(d[0].split()) if s == 'OK' and d[0] else 0
print(f'Reste INBOX: {remaining}')
```

### Creating IMAP folders

```python
mail.create('"Folder/Subfolder"')
# ALWAYS quote the full folder path with double quotes inside single quotes
```

### Folder naming convention

```
IT/OVH
IT/Cloud
IT/SAP
IT/GitHub
```

---

### Protecting Senders

Update `scripts/config.json` whenever the user says "keep" or "don't delete":

```json
"protected_senders": {
  "list": [
    "noreply@newsletter.com",
    "no-reply@tickets.vendor.com",
    "invoices@provider.com"
  ]
}
```

Also add routing rules for predictable senders (e.g., invoices → Finance, cloud provider → IT) in the `routing.rules` section.

---

### Complete Python Template (Delete All)

```python
import imaplib
with open('/path/to/config.json') as f:
    import json; cfg = json.load(f)
mail = imaplib.IMAP4_SSL(cfg['imap']['server'], cfg['imap']['port'])
mail.login(cfg['imap']['username'], cfg['imap']['password'])
mail.select('INBOX')

s, d = mail.uid('SEARCH', None, 'FROM', 'sender@example.com')
uids = d[0].split()
total = len(uids)
print(f'Deleting {total}...')
mail.uid('STORE', ','.join(u.decode() for u in uids), '+FLAGS', r'(\Deleted)')
mail.expunge()
print(f'Done. {total} deleted')
mail.logout()
```

### Complete Python Template (Move & Delete)

```python
s, d = mail.uid('SEARCH', None, 'FROM', 'sender@example.com')
uids = d[0].split()
chunk = 50
dest = '"Gestion Interne/Finance-Compta"'
for i in range(0, len(uids), chunk):
    c = uids[i:i+chunk]
    uid_str = ','.join(u.decode() for u in c)
    mail.uid('COPY', uid_str, dest)
    mail.uid('STORE', uid_str, '+FLAGS', r'(\Deleted)')
mail.expunge()
```

---

### Pitfalls to Avoid

- ❌ **Don't loop UID.COPY one-by-one** — takes 30+ seconds for >100 emails
- ❌ **Don't use `datetime.strptime` for email dates** — always use `parsedate_to_datetime`
- ❌ **Don't forget to quote folder names** — use `'"Folder/Name"'` for CREATE, COPY, SELECT
- ❌ **Don't use `mail.select('[Gmail]/All Mail')`** — it fails. Use raw command: `mail._simple_command('SELECT', '"[Gmail]/All Mail"')` then set `mail.state = 'SELECTED'`
- ❌ **Don't unsubscribe if sender is in `protected_senders`**
- ❌ **Don't use `SUBJECT` search with special characters (é, à, etc.)** — IMAP can't encode them. Use `TEXT` search instead or scan UIDs
```

---

## 🔐 Security Notes

- **Credentials**: Your IMAP password is stored in `scripts/config.json`. Keep this file secure — don't commit it to git. The setup script stores it with restricted permissions.
- **App Passwords**: For Gmail, always use an App Password, not your main password. Create one at https://myaccount.google.com/apppasswords
- **IMAP access**: Some providers require "Less secure app access" or specific IMAP settings. Check your provider's documentation.
- **Invoice storage**: Ensure the invoice directory has appropriate backups.

## 📞 Supported Providers

| Provider | IMAP Server | Port | Notes |
|----------|------------|------|-------|
| Gmail / Google Workspace | `imap.gmail.com` | 993 | Requires App Password with 2FA |
| Outlook.com / Hotmail | `outlook.office365.com` | 993 | Use regular password or app password |
| Office 365 / Exchange | `outlook.office365.com` | 993 | Org admin may restrict IMAP |
| Yahoo Mail | `imap.mail.yahoo.com` | 993 | App password recommended |
| iCloud | `imap.mail.me.com` | 993 | App-specific password required |
| Custom (any IMAP) | your server | 143 or 993 | For self-hosted or corporate mail |

## 📂 Skill Files Reference

```
email-manager/
├── SKILL.md                    ← This file — skill instructions
├── scripts/
│   ├── config.json             ← Edit with your IMAP credentials
│   ├── fetch_emails.py         ← IMAP fetcher → JSON
│   ├── extract_invoices.py     ← Invoice detection & metadata
│   └── setup.sh                ← One-time interactive setup
├── references/
│   ├── CATEGORIES.md           ← Category taxonomy (edit to customize)
│   └── user_preferences.json   ← Learned categorization rules (auto-created)
```
