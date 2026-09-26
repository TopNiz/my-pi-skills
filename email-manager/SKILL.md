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

6. Create the skill environment with **uv** (dependencies are declared in `pyproject.toml`):

```bash
cd ~/.agents/skills/email-manager
uv sync                        # creates .venv from pyproject.toml + uv.lock
```

Refresh-token storage is platform-specific: macOS uses the Keychain, Linux the Secret
Service, and Windows a plain file (`token.gmail.json`). The `auth.py --migrate` command only
applies to macOS/Linux, where it imports legacy local OAuth files into the native store.

> ⚠️ **Never install these dependencies with `pip install --target .deps`.** On Windows, pip
> stages wheels in a `mkdtemp()` tree (mode `0o700`) and then `shutil.move`s them into place.
> The rename carries that DACL with it, so every installed file gets
> `D:P(A;OICI;FA;;;OW)(FA;;;SY)(FA;;;BA)` — owner-only, inheritance **disabled**. Anything that
> is not the owner (sandboxed agents, other accounts, services) is then denied, and
> `OW`/OWNER RIGHTS silently hides the damage from the owner. `uv sync` inherits ACLs
> correctly and is immune. If a tree is already damaged: `icacls <dir> /reset /T /C /Q`.
>
> `auth.py` and `fetch_emails.py` transparently re-exec into `.venv`, so `python3 scripts/...`
> and `uv run python scripts/...` both work.

On Windows, both files are plain local files: `credentials.gmail.json` holds the OAuth client
configuration and `token.gmail.json` holds the refresh token. Windows Credential Manager is
**not** used — non-interactive and sandboxed processes cannot reach it (`WinError 1312`), so
the file store works everywhere.

7. **OAuth consent screen**: If needed, set to "External" and add your email as a test user

### 2. Authenticate

```bash
cd ~/.agents/skills/email-manager
python3 scripts/auth.py
```

This opens your browser → click "Allow" → on macOS the refresh token goes to the Keychain and
on Linux to the Secret Service/GNOME Keyring (no token file retained). On Windows it is written
to `token.gmail.json` in the skill directory. Done.

### 3. Verify auth

```bash
python3 scripts/auth.py --check
```

Resolves the mailbox with `users.getProfile`, so it prints the account's Google
**primary** address — the authoritative answer to "which account is this?":

```
Authenticated as nizar.ayed@chain-it.com using the file token store.
```

Exit codes: `0` = credentials work against the Gmail API; `1` = refresh token
missing, rejected (`invalid_grant`, revoked/expired), or the API was unreachable.
Because it makes one API call, it is no longer a purely offline check.

### 4. Troubleshoot: other agents or machines cannot authenticate

Where credentials live is **per platform**:

| Platform | Refresh token | OAuth client config |
|---|---|---|
| Windows | `token.gmail.json` (file, gitignored) | `credentials.gmail.json` (file, gitignored) |
| macOS | Keychain (`keyring`) | Keychain (imported with `--migrate`) |
| Linux | Secret Service (`secret-tool`) or systemd credentials | Secret Service or systemd credentials |

Windows needs no OS credential store at all: `auth.py` reads and writes `token.gmail.json`
directly, so sandboxed agents and services (which cannot use Credential Manager) work without
`PI_EMAIL_MANAGER_TOKEN_FILE`. The environment variable is only needed on macOS/Linux to opt
into a file store.

```bash
python3 scripts/auth.py --diagnose   # exit 0 usable / 1 needs provisioning; prints no secrets
```

| What `--diagnose` says | Meaning | Fix |
|---|---|---|
| `refresh-token: present` → `OK` | fine | — |
| `refresh-token: ABSENT`, client config present | next attempt needs a browser | provision a token (below) |
| client config `ABSENT` as well | OAuth cannot even start | copy `credentials.gmail.json` here (it is gitignored), then authenticate |
| `refresh FAILED: invalid_grant` | token revoked or expired | `python3 scripts/auth.py` |

**Windows** — because the token is a file, provisioning a machine or agent is just copying it:

```powershell
# from an already-authenticated machine (e.g. via the interactive session)
python .\scripts\auth.py --export .\token.gmail.json
# then copy token.gmail.json into the target skill dir; no env var, no --migrate
```

If `auth.py` was run from a **service or sandboxed** session with no interactive desktop, the
browser consent cannot be completed there. Run consent once in a normal interactive terminal
(or export `token.gmail.json` from one) and the file store is picked up automatically.

> ⚠️ A token file holds a `gmail.modify` refresh token. Keep it inside the skill directory
> (gitignored) and delete it once the agent no longer needs it.

**macOS / Linux** — `PI_EMAIL_MANAGER_TOKEN_FILE` opts into the same file store and takes
precedence over the OS credential store; it is read *and* written. To import legacy files into
the native store, run `python scripts/auth.py --migrate` (on Windows this is a no-op, since the
file already *is* the store).

**Provisioning another machine:** copy `credentials.gmail.json` (not in Git), then run the
consent once there. On macOS/Linux you can instead `--export` here and `--migrate` there; on
Windows just copy `token.gmail.json` across.

### Always-on Linux machines: systemd-encrypted credentials

For a 24/7 Linux monitor, do not rely on a desktop keyring that may lock when no graphical session is active. Store the Gmail OAuth client configuration and refresh-token JSON as host-bound, user-scoped systemd credentials, then load them into the service with `LoadCredentialEncrypted=`. The service receives decrypted read-only files only under `$CREDENTIALS_DIRECTORY` at runtime; no plaintext OAuth files are retained and nothing is committed to Git.

Use credential names `gmail-oauth-client` and `gmail-oauth-token`. Generate the encrypted files with `systemd-creds encrypt --user --with-key=host`; encrypt from standard input so secrets never appear in command arguments or terminal output. The `auth.py` helper automatically prefers those runtime credentials and refreshes access tokens in memory.

### 4. Configure your mailbox

Edit `scripts/config.json` — the Gmail API needs no IMAP server/port and no
account block: a mailbox is addressed by `userId="me"`, so the config is **flat
and account-agnostic**. `scripts/config.template.json` is the canonical shape:

```json
{
  "filters": {
    "max_emails": 50,
    "fetch_days_back": 7,
    "include_seen": false,
    "folders": ["INBOX"]
  },
  "invoices": {
    "storage_dir": "~/Invoices",
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
```

**No passwords in config.json** — OAuth2 handles everything.

The account email is deliberately **not** in the config. `fetch_emails.py`
resolves the mailbox via `users.getProfile(userId="me")`, which returns the
**primary** address of the authenticated Google account — never a send-as alias
that merely delivers to the same inbox.

> ⚠️ **Aliases are the same mailbox but not the same address.** If
> `nizar.ayed@upgrade-code.org` is a send-as alias of the account whose primary
> is `nizar.ayed@chain-it.com`, mail to either lands in the one inbox, yet the API
> only ever reports `nizar.ayed@chain-it.com`. So:
> - Take the account label from the `"account"` field of the `fetch_emails.py`
>   JSON output. Never infer it from a message's `To:`/`Cc:` header, a reply-to,
>   or a newsletter's unsubscribe URL — those show whichever alias the sender used.
> - `--account=<email>` must be the **primary** address; an alias aborts the fetch
>   with `Authenticated as <primary>, but --account=<alias> requested`. In this
>   single-mailbox setup, simply omit `--account`.
> - `python3 scripts/auth.py --check` (and `auth.py` with no flags) resolves the
>   mailbox with `users.getProfile` and prints `Authenticated as
>   <primary-address>.`, so the reported address is always the primary one.

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

**Use the mailbox address from the JSON, not from the messages.** Each account entry in the
output carries an `"account"` field (e.g. `"account": "nizar.ayed@chain-it.com"`) — that is
the Google primary address. Render it in the headers below verbatim. Do **not** use the
address seen in a message's `To:`/`Cc:` header or a newsletter's unsubscribe link: those may
show a send-as alias of the same mailbox (e.g. `nizar.ayed@upgrade-code.org`) and will
misreport the account.

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
│ Account: <accounts[].account from the JSON>          │
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

### ✍️ Email Authoring and Drafting

When the user asks to draft any email — a reply, a new message, a report, a summary, or an invoice email — use the **[email-authoring](../email-authoring/SKILL.md)** skill to generate the content:

1. **Load the email-authoring skill** — Read `../email-authoring/SKILL.md` and `../email-authoring/references/STYLE-GUIDE.md`
2. **Use contact context for replies** — For a reply or a known recipient, check `../email-authoring/contacts/index.json` and read the matching message history when available. Do not require contact history for new emails.
3. **Match language and tone** — Apply the authoring guidance and choose the appropriate language-specific signature.
4. **Apply presentation templates** — For structured content such as reports, summaries, invoices, readings, or comparisons, use `../email-authoring/references/EMAIL-TEMPLATES.md`, including its stylesheet, container, headings/tables, and visual hierarchy.
5. **Use the correct signature** — Use the French or English HTML signature from `STYLE-GUIDE.md` section 11, populated from `../email-authoring/config/signature.json`, unless a documented personal-message exception applies.
6. **Create the Gmail draft** — Use the Gmail API `drafts.create()` with `multipart/alternative` (HTML + plain text) and leave `To` empty when the user asks for an unaddressed draft.
7. **Wait for confirmation before sending** — Never send without explicit user approval.

> The email-authoring skill handles **authoring style** (tone, greeting, language) and **presentation style** (HTML layout, structured templates, and signatures). The email-manager skill handles Gmail transport, fetching, draft creation, and sending safeguards.

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
│ Account: <accounts[].account from the JSON>          │
└─────────────────────────────────────────────────────┘

📥 RECEIVED TODAY (15 emails)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📧 <accounts[].account from the JSON> (15 emails)

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
The lists are top-level (there is no `accounts` wrapper):

```json
{
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
- ❌ **Don't commit or print OAuth tokens** — `token.gmail.json` is a gitignored secret holding the refresh token (always on Windows; on macOS/Linux only when using the file store)

---

## 🔐 Security Notes

- **OAuth2** — No passwords stored. Authentication is via Google's OAuth2 flow.
- **Credential storage** — Refresh tokens live in macOS Keychain or Linux Secret Service/GNOME Keyring. On Windows they live in the gitignored `token.gmail.json` file, never committed or printed.
- **OAuth client configuration** — `credentials.gmail.json` (gitignored) is used directly on Windows; macOS/Linux import it into the native credential store with `auth.py --migrate`.
- **File token store** — `token.gmail.json` is read/written directly on Windows; on macOS/Linux it is used only when `PI_EMAIL_MANAGER_TOKEN_FILE` is set, and `--migrate` imports it into the native store and removes the file.
- **Revoke access** at https://myaccount.google.com/permissions anytime.
- **Invoice storage**: Ensure the invoice directory has appropriate backups.
- **Scope**: `gmail.modify` — required for reading, deleting, and moving emails.

## 📂 Skill Files Reference

```
email-manager/
├── SKILL.md                    ← This file — skill instructions
├── pyproject.toml              ← Dependency declarations (source of truth)
├── uv.lock                     ← Pinned, reproducible dependency set
├── .venv/                      ← uv-managed environment (`uv sync`; gitignored)
├── scripts/
│   ├── config.json             ← Account config (no passwords!)
│   ├── config.template.json    ← Canonical flat config shape
│   ├── auth.py                 ← Gmail OAuth2 (Keychain/Secret Service; file store on Windows)
│   ├── fetch_emails.py         ← Gmail API email fetcher → JSON
│   ├── extract_invoices.py     ← Invoice detection & metadata
│   └── setup.sh                ← One-time interactive setup (legacy)
├── references/
│   ├── CATEGORIES.md           ← Category taxonomy (edit to customize)
│   └── user_preferences.json   ← Learned categorization rules (auto-created)
```

### Runtime environment

Dependencies live in `pyproject.toml` and are installed by `uv`:

```bash
uv sync                  # create/refresh .venv to match uv.lock
uv lock --upgrade        # bump the locked versions
uv run python scripts/fetch_emails.py scripts/config.json
```

`keyring` is pulled in on macOS only (`sys_platform` marker); Linux uses the system
`secret-tool`, and Windows uses the file store. To add a dependency, edit `pyproject.toml`
then run `uv sync` — do **not** reintroduce a `--target` directory or a `requirements*.txt` file.

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
| Auth storage | macOS Keychain | Keychain/Secret Service, or file store on Windows (OAuth2) |

> **Note:** The `_gmail_labels` and `thread_id` fields are added to each email in the JSON output for use in Gmail API operations (delete, move, etc.).
