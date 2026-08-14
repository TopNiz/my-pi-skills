---
name: reply-style
description: Answer messages by imitating your writing style. Fetches your sent emails from IMAP, builds per-contact style profiles, and drafts replies in your voice — matching the language and tone you use with each person. Supports email, Slack, LinkedIn, SMS, and any messaging platform.
allowed-tools: read write edit bash
---

# 🗣️ Reply Style Skill

Drafts replies to messages by learning **your personal writing style per contact** (tone, language, greeting, sign-off) and your **preferred presentation style** (HTML formatting, tables, structured layouts). Instead of generic AI-sounding responses, get replies that sound like *you* and look like *you*.

---

## 🚀 Quick Start (One-Time Setup)

### Prerequisites

Your email password is already stored in macOS Keychain (from the [email-manager](../email-manager/SKILL.md) skill setup).
Use the email you configured in `config/signature.json`:

```bash
security find-generic-password -a "your.email@example.com" -s "email-manager" -w
```

If it's not there yet, add it:

```bash
security add-generic-password -a "your.email@example.com" -s "email-manager" -w "YOUR_APP_PASSWORD" -U
```

### Step 1 — Fetch Your Sent Messages

Build the contact database from your last 6 months of sent emails:

```bash
cd ~/.agents/skills/reply-style
python3 scripts/fetch_sent.py scripts/config.json
```

This will:
- Connect to your Gmail account via IMAP
- Read the `[Gmail]/Sent Mail` folder
- Extract messages sent in the last 6 months
- Group them by recipient
- Save per-contact message files in `contacts/messages/`
- Create the master `contacts/index.json`

> **⏱ Takes ~1-2 minutes** depending on how many messages you've sent.

### Step 2 — Rebuild Index & Detect Languages

```bash
python3 scripts/rebuild_contacts.py scripts/config.json
```

This detects the language you use with each contact (French, English, Arabic) and rebuilds the index.

### Step 3 — Auto-learn Categories (Optional but Recommended)

Let the LLM analyze your contacts and suggest categories. Run this manually by asking:

> *"Analyze my contacts and suggest categories based on our conversations."*

The agent will read the contact files and categorize each person as:
- `client` — Professional/business context
- `colleague` — Work or project collaborator
- `family` — Family member
- `friend` — Personal friend
- `service` — Service provider/support
- `other` — Uncategorized by default

You can also set categories manually:

> *"Set john@example.com as a client"*

---

## 📬 Core Workflow: Reply to a Message

### How it works

1. You receive a message (email, Slack, LinkedIn, SMS — any platform)
2. You say: **"Reply to this in my style"**
3. The agent:
   - Looks up the sender in `contacts/index.json`
   - Reads your past messages to that person from `contacts/messages/<email>.json`
   - Identifies the language of the incoming message
   - Considers the contact's category (client, friend, etc.)
   - Drafts 2-3 reply options in **your specific voice**

### Usage examples

```
User: "Reply to this email in my style:
       Hi Nizar, can we reschedule our meeting to Thursday? — Sarah"

Agent: [Looks up sarah@example.com in contacts, reads past messages,
        detects English, sees category: client]

       Here are 2 replies in your style:

       Option 1 – Direct & friendly:
       "Hi Sarah, Thursday works for me. Same time? Let me know."

       Option 2 – More detailed:
       "Hi Sarah, Thursday works perfectly. Is 2pm still good for you?
        Let me know if anything changes. — Nizar"
```

```
User: "Réponds à ce message dans mon style :
       Salut Nizar, tu peux vérifier le devis stp ? — Marc"

Agent: [Looks up marc@example.com, reads past messages in French,
        detects category: colleague]

       Option 1 – Naturel :
       "Salut Marc, je regarde ça et je te reviens dans la journée."

       Option 2 – Plus formel :
       "Bonjour Marc, je vais vérifier le devis et te fais un retour
        rapidement. Bonne journée."
```

### Key behavior rules

The agent must follow these rules when drafting replies:

1. **Contact lookup first** — Always check `contacts/index.json` first. If the contact exists, read their message file.

2. **Language match** — Reply in the **same language** as the incoming message. If the incoming message is in French, reply in French. If English, reply in English.

3. **Style imitation** — Analyze the stored messages for:
   - **Greeting style** (Bonjour / Salut / Hey / Coucou / Cher / Hi / Hello / nothing)
   - **Sentence length** (short & punchy vs. detailed & explanatory)
   - **Punctuation** (lots of exclamation marks, ellipses, or minimal)
   - **Emoji usage** (frequent, occasional, never)
   - **Sign-off** (Cordialement / Bien / A+ / Cheers / nothing / just name)
   - **Formal register** ("vous" vs "tu" in French, "Dear" vs "Hey" in English)
   - **Paragraph vs. bullet structure**
   - **Typical response length** (1 sentence, short paragraph, multi-paragraph)
   - **Signature used** — Always append the correct signature based on the reply language (see signatures below)

4. **Category adaptation** — Adjust tone based on contact category:
   - `client` → professional, clear, structured
   - `colleague` → collaborative, direct, often short
   - `family` → warm, personal, emoji-friendly
   - `friend` → casual, playful, relaxed
   - `service` → polite, specific, reference numbers
   - `unknown` → slightly more formal, matching message language

5. **No contact found** — If the sender is not in your database:
   - Reply in the same language as the incoming message
   - Use a generally appropriate tone (slightly formal, matching message)
   - Offer to save this contact for future style learning

6. **Provide options** — Always offer 2-3 reply options with brief notes (e.g., "Short & direct" / "More detailed" / "Warm & friendly")

7. **Context awareness** — Consider the subject/topic when relevant. If the message is about an invoice, keep the reply business-appropriate even if you're usually casual with that contact.

### 📝 Signature Rules (CRITICAL)

Your signature is an important part of every email. There are **two versions** — one for French replies and one for English replies. **Always append the correct signature based on the language of the reply.**

Use **HTML signatures** when sending HTML-formatted replies. Use **plain text signatures** when sending plain text replies.

> **Personal data**: Your real phone, email, and social links are stored in `config/signature.json` (gitignored).
> Copy `config/signature.example.json` to `config/signature.json` and fill in your details.
> The templates below use placeholders — the script will substitute real values from the config.

#### French signature — HTML (for all French HTML replies)

Uses your Chain-IT Apple Mail signature colors: **red `#d81e00`** and **grey `#797979` / `#424242`**. Preserve these colors and the Futura font when creating HTML drafts.

```html
<div>
  <div dir="auto" style="caret-color: rgb(0, 0, 0); color: rgb(0, 0, 0); letter-spacing: normal; text-align: start; text-indent: 0px; text-transform: none; white-space: normal; word-spacing: 0px; text-decoration-line: none; overflow-wrap: break-word; -webkit-nbsp-mode: space; line-break: after-white-space;">
    <div>
      <font face="Futura"><font size="4"><span style="font-style: normal;"><font color="#d81e00">Chain-</font><font color="#797979">IT&nbsp;</font><font color="#d81e00">. com</font></span></font><br></font>
    </div>
    <div>
      <font face="Futura">
        <font color="#424242"><b>{{NAME}}</b></font><br>
        <font color="#424242">{{TITLE}}</font><br><br>
        <font color="#424242">FR Mobile :</font><span class="Apple-tab-span" style="color: rgb(66, 66, 66); white-space: pre;">	</span><font color="#424242">{{PHONE}}</font><br>
        <font color="#424242">eMail:<span class="Apple-tab-span" style="white-space: pre;">		</span>{{EMAIL}}<br>Web:<span class="Apple-tab-span" style="white-space: pre;">		</span>{{WEBSITE}}</font><br>
        <font color="#424242">______________________________________________________________</font><br>
        <font color="#424242">Ce message et toutes les pièces jointes sont établis&nbsp;à l'intention exclusive de ses destinataires et sont&nbsp;confidentiels. Si vous recevez ce message par&nbsp;erreur, merci de le détruire et d'en avertir&nbsp;immédiatement l'expéditeur. Toute utilisation ou&nbsp;diffusion non autorisée de ce message est interdite.</font><br>
        <font color="#424242">Internet ne permettant pas d'assurer l'intégrité de ce&nbsp;message, Chain-IT.com décline toute&nbsp;responsabilité en cas d'altération ou de&nbsp;modification.</font><br>
        <font color="#424242">&nbsp;</font><br>
        <font color="#424242">Pensez à l'environnement, n'imprimez ce message&nbsp;qu'en cas de nécessité !</font><br>
        <font color="#999" style="font-size: 11px;">🤖 Message généré par IA et approuvé par lui ✨</font>
      </font>
    </div>
  </div>
</div>
```

> **⚠️ Real tab characters:** The `Apple-tab-span` elements in the HTML signature above contain **real tab characters**, not the literal text `\t`. Keep the actual tab characters when copying — a literal `\t` renders as "\t" in the email and breaks the column alignment.

#### French signature — Plain text (for French plain text replies)

```
Chain-IT . com
{{NAME}}
{{TITLE}}

FR Mobile :	{{PHONE}}
eMail:		{{EMAIL}}
Web:		{{WEBSITE}}
______________________________________________________________
Ce message et toutes les pièces jointes sont établis à l'intention exclusive de ses destinataires et sont confidentiels. Si vous recevez ce message par erreur, merci de le détruire et d'en avertir immédiatement l'expéditeur. Toute utilisation ou diffusion non autorisée de ce message est interdite.
Internet ne permettant pas d'assurer l'intégrité de ce message, Chain-IT.com décline toute responsabilité en cas d'altération ou de modification.

Pensez à l'environnement, n'imprimez ce message qu'en cas de nécessité !
🤖 Message généré par IA et approuvé par lui ;-)
```

#### English signature — HTML (for all English HTML replies)

Same Apple Mail styling, adapted for English.

```html
<div>
  <div dir="auto" style="caret-color: rgb(0, 0, 0); color: rgb(0, 0, 0); letter-spacing: normal; text-align: start; text-indent: 0px; text-transform: none; white-space: normal; word-spacing: 0px; text-decoration-line: none; overflow-wrap: break-word; -webkit-nbsp-mode: space; line-break: after-white-space;">
    <div>
      <font face="Futura"><font size="4"><span style="font-style: normal;"><font color="#d81e00">Chain-</font><font color="#797979">IT&nbsp;</font><font color="#d81e00">. com</font></span></font><br></font>
    </div>
    <div>
      <font face="Futura">
        <font color="#424242"><b>{{NAME}}</b></font><br>
        <font color="#424242">{{TITLE}}</font><br><br>
        <font color="#424242">Mobile:</font><span class="Apple-tab-span" style="color: rgb(66, 66, 66); white-space: pre;">	</span><font color="#424242">{{PHONE}}</font><br>
        <font color="#424242">Email:<span class="Apple-tab-span" style="white-space: pre;">		</span>{{EMAIL}}<br>Web:<span class="Apple-tab-span" style="white-space: pre;">		</span>{{WEBSITE}}</font><br>
        <font color="#424242">______________________________________________________________</font><br>
        <font color="#424242">This message and any attachments are intended solely for their recipients and are confidential. If you received this message in error, please delete it and notify the sender immediately. Any unauthorized use or distribution is prohibited.</font><br>
        <font color="#424242">Because internet communications cannot guarantee message integrity, Chain-IT.com accepts no liability for alteration or modification.</font><br>
        <font color="#424242">&nbsp;</font><br>
        <font color="#424242">Please consider the environment before printing this message.</font><br>
        <font color="#999" style="font-size: 11px;">🤖 AI generated message and approved by him ✨</font>
      </font>
    </div>
  </div>
</div>
```

#### English signature — Plain text (for English plain text replies)

```
Chain-IT . com
{{NAME}}
{{TITLE}}

Mobile:	{{PHONE}}
Email:	{{EMAIL}}
Web:	{{WEBSITE}}
______________________________________________________________
This message and any attachments are intended solely for their recipients and are confidential. If you received this message in error, please delete it and notify the sender immediately. Any unauthorized use or distribution is prohibited.
Because internet communications cannot guarantee message integrity, Chain-IT.com accepts no liability for alteration or modification.

Please consider the environment before printing this message.
🤖 AI generated message and approved by him ;-)
```

> **Rule:** If the reply is in French → use the French signature. If the reply is in English → use the English signature. The language of the message dictates the signature language, regardless of the recipient.

> **Format rule:** All replies must be in **HTML format** with the HTML signature. Always use the HTML signature regardless of the incoming message format. Plain text replies are never acceptable.

> **Short replies (1-2 sentences):** For very short replies (like "Bien reçu !" or "I'm there"), the signature is optional — match what you've done historically with that contact.

> **Family/personal contacts:** For family members (like Sonia, category: family), you typically don't include a full signature. Just your first name or nothing. Follow the pattern from your past messages with that person.

8. **Draft → Confirm → Send** — Never send a message directly. Always:
   - **Step 1 — Draft**: Present the reply option(s) to the user
   - **Step 2 — Confirm**: Wait for the user to approve, request changes, or choose an option
   - **Step 3 — Send**: Only after the user explicitly confirms ("Send it", "Yes", "Go ahead"), proceed to send the message

---

## 📐 Presentation Style vs Authoring Style

This skill covers **two distinct dimensions** of your communication:

| Dimension | What it captures | Defined in |
|-----------|-----------------|------------|
| **Authoring style** 🗣️ | Tone, greeting, sign-off, language (fr/en), formality, sentence structure, emoji use | `STYLE-GUIDE.md` + per-contact message history |
| **Presentation style** 📊 | HTML formatting, tables, structured layouts, colors, visual hierarchy | `EMAIL-TEMPLATES.md` |

### Authoring Style (original purpose)

Learned from your past sent messages per contact — how *you* write, not how an AI would write. The agent analyzes your greeting style, sentence length, punctuation, emoji usage, sign-off, and formality register, then mirrors it in replies.

### Presentation Style (added)

For structured emails containing data tables (invoices, readings, comparisons, reports), use the content templates defined in [`references/EMAIL-TEMPLATES.md`](references/EMAIL-TEMPLATES.md). These enforce a consistent visual identity across your structured emails.

These templates provide:
- A **base stylesheet** with consistent colors (`#2563eb` headers, `#dc2626` totals, alternating row stripes)
- **2-column table templates** for key-value data
- **Multi-section layouts** for complex emails with multiple data groups
- A **full email layout** combining content tables + the standard signature from this skill

### When to apply each

| Scenario | Authoring style | Presentation style |
|----------|----------------|-------------------|
| Casual message ("See you tomorrow") | ✅ Match your tone | ❌ No template needed |
| Invoice / bill breakdown | ✅ Match your tone | ✅ Tables make amounts clear |
| Meter/reading comparison | ✅ Match your tone | ✅ Structured data |
| Forwarded content | ✅ Match your tone | ❌ Preserve original |

### How to apply presentation templates

1. **Read** `references/EMAIL-TEMPLATES.md`
2. **Include the `<style>` block** in the `<head>` of your HTML
3. **Wrap content** in `<div class="container">`
4. **Use `<h2>` + `<table>`** for each data section
5. **Append the signature** from `STYLE-GUIDE.md` section 11 (French or English)
6. **Always send multipart/alternative** (HTML + plain text fallback)

---

## 📖 Learning Workflow: Add New Style Examples

You can teach the skill your style for specific contacts or general preferences.

### Add a contact manually

```
User: "Learn from this message I sent:
       Hey John, thanks for the update. Let's sync next week.
       I'll send a calendar invite. Cheers!"
```

The agent should:
1. Extract the recipient if identifiable
2. Save the message to the contact's file
3. Update the index

### Set a category

```
User: "Categorize marie@domain.com as a client"
```

The agent updates `contacts/index.json`:
```json
{
  "marie@domain.com": {
    "name": "Marie",
    "category": "client",
    "language": "fr",
    "message_count": 12,
    "file": "marie_domain_com.json"
  }
}
```

### Update global style preferences

```
User: "I prefer using 'Cordialement' as sign-off for all clients"
```

The agent notes this as a global preference (no file change needed — applies during reply generation).

---

### 🚨 Important: Clean your contact data

Fetched sent messages may include AI-generated messages (messages written by an AI on your behalf) or auto-generated calendar invites. These **do not reflect your personal style**.

**Before using the skill to reply, review the contact's messages and remove any that aren't genuinely yours:**

```bash
# Example: remove the first message from Sonia's contact file
cd ~/.agents/skills/reply-style
python3 -c "
import json
with open('contacts/messages/sonia_tfifha_at_yahoo_dot_fr.json') as f:
    c = json.load(f)
# Remove AI-generated messages (adjust index as needed)
c['messages'] = [m for m in c['messages'] if 'votre' not in m.get('body','').lower()[:50]]
with open('contacts/messages/sonia_tfifha_at_yahoo_dot_fr.json', 'w') as f:
    json.dump(c, f, ensure_ascii=False, indent=2)
"
```

**Pro tip:** After cleaning, update the index:
```bash
python3 scripts/rebuild_contacts.py scripts/config.json
```

---

## 🔄 Re-fetch Sent Messages (Keep Database Updated)

To stay current, re-fetch periodically:

```bash
cd ~/.agents/skills/reply-style
python3 scripts/fetch_sent.py scripts/config.json
python3 scripts/rebuild_contacts.py scripts/config.json
```

This refreshes the database with new sent messages. Existing categories are preserved.

---

## 📁 File Reference

```
reply-style/
├── SKILL.md                       ← This file
├── scripts/
│   ├── config.json                ← Account configuration (reuses email-manager Keychain)
│   ├── fetch_sent.py              ← Fetch sent messages from IMAP
│   ├── rebuild_contacts.py        ← Rebuild index and detect languages
│   └── send_email.py              ← Send email via SMTP (Gmail)
├── contacts/                      ← Auto-created contact database
│   ├── index.json                 ← Master contact list with categories
│   └── messages/                  ← Per-contact message files
│       ├── user_gmail_com.json    ← Messages sent to user@gmail.com
│       ├── sarah_company_com.json ← Messages sent to sarah@company.com
│       └── ...
└── references/
    ├── STYLE-GUIDE.md             ← Reference for style analysis criteria
    └── EMAIL-TEMPLATES.md          ← HTML content templates (tables, layouts)
```

### Contact file format (`contacts/messages/<email>.json`)

```json
{
  "email": "john@example.com",
  "name": "John Doe",
  "category": "client",
  "language": "en",
  "messages": [
    {
      "date": "2026-05-14T10:00:00",
      "subject": "Re: Meeting tomorrow",
      "body": "Hey John, Thursday works for me. Same time? See you then."
    },
    {
      "date": "2026-05-01T15:30:00",
      "subject": "Project update",
      "body": "Hi John, here's the latest status on the project. We're on track for the June deadline. Let me know if you have any questions."
    }
  ]
}
```

### Index format (`contacts/index.json`)

```json
{
  "john@example.com": {
    "name": "John Doe",
    "category": "client",
    "language": "en",
    "message_count": 2,
    "file": "john_example_com.json"
  },
  "marie@example.com": {
    "name": "Marie Dupont",
    "category": "friend",
    "language": "fr",
    "message_count": 15,
    "file": "marie_example_com.json"
  }
}
```

---

## 🧠 Tips

- **More examples = better style matching.** The more messages you have stored for a contact, the more accurately the agent can replicate your style.
- **Refresh monthly.** Run `fetch_sent.py` once a month to keep your contact database current.
- **Explicit feedback works.** If a generated reply doesn't sound like you, say: *"Make it shorter"* or *"Use 'Salut' instead of 'Bonjour'"* — the agent will adjust on the fly.
- **The agent doesn't save new style examples permanently** unless you explicitly ask: *"Save this exchange"* or *"Learn from this message."*
- **For new contacts**, the agent uses your general style in the appropriate language. You can then optionally save the exchange for future reference.

---

## 📤 Sending Emails (SMTP)

To actually send the confirmed reply, the agent uses `scripts/send_email.py`:

```bash
# Plain text (default)
python3 scripts/send_email.py scripts/config.json "recipient@example.com" "Subject" /tmp/body.txt

# HTML formatted (explicit)
python3 scripts/send_email.py scripts/config.json "recipient@example.com" "Subject" /tmp/body.html --html

# HTML with manual plain text fallback (recommended)
python3 scripts/send_email.py scripts/config.json "recipient@example.com" "Subject" /tmp/body.html --html --alt /tmp/body_fallback.txt
```

This sends via **Gmail SMTP** (`smtp.gmail.com:587`, TLS) using the same App Password from your macOS Keychain.

### HTML support

The script **auto-detects HTML** — if the body file contains HTML tags (`<p>`, `<br>`, `<div>`, etc.), it's sent as HTML automatically with a plain text fallback extracted from the HTML. You can also force HTML mode with `--html`.

When sending HTML, the script creates a `multipart/alternative` message containing both:
- A plain text version (for email clients that don't render HTML)
- The HTML version (for modern clients)

### 🚨 Critical pitfall: Never pass a raw .eml / MIME file as the body

`send_email.py` treats the body file as **content**, not as a raw email. If you pass a file containing MIME headers, multipart boundaries, or base64-encoded attachments, the script wraps that whole thing **inside another MIME message**, causing:
- **Double-MIME corruption** — the raw .eml is re-encapsulated, making it unreadable
- **Attachments lost** — base64 placeholders are sent literally instead of actual files
- **Nested multipart garbage** — the recipient sees a garbled message

✅ **Correct usage — body file contains ONLY the message text or HTML:**
```bash
# body.html contains <p>Bonjour...</p> — no MIME headers
python3 send_email.py config.json "to@example.com" "Subject" /tmp/body.html --html
```

❌ **NEVER do this — body file is a raw .eml with MIME structure:**
```bash
# body.eml has Subject:/From:/To: headers + boundaries + base64
python3 send_email.py config.json "to@example.com" "Subject" /tmp/body.eml --html  # ← BROKEN
```

### 🚨 Critical pitfall: `send_email.py` does NOT support attachments

The script only handles `text/plain` or `text/html` bodies. If you need to attach files (PDF, images, etc.), you **must use Python's `smtplib` directly** with a `MIMEMultipart('mixed')` message:

```python
import smtplib, subprocess, json, base64, email.utils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Get password from keychain
pw = subprocess.run(
    ['security','find-generic-password','-a','your@email.com','-s','email-manager','-w'],
    capture_output=True, text=True
).stdout.strip()

# Build mixed MIME
msg = MIMEMultipart('mixed')
msg["From"] = "your@email.com"
msg["To"] = "recipient@example.com"
msg["Subject"] = "Re: Subject"
msg["Date"] = email.utils.formatdate(localtime=True)

# Alternative body (plain + HTML)
alt = MIMEMultipart('alternative')
alt.attach(MIMEText("Hello", 'plain', 'utf-8'))
alt.attach(MIMEText("<p>Hello</p>", 'html', 'utf-8'))
msg.attach(alt)

# PDF attachment
with open("/path/to/file.pdf", 'rb') as f:
    pdf_data = f.read()
att = MIMEBase('application', 'pdf')
att.set_payload(pdf_data)
encoders.encode_base64(att)
att.add_header('Content-Disposition', 'attachment', filename="document.pdf")
msg.attach(att)

# Send
server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()
server.login("your@email.com", pw)
server.sendmail("your@email.com", ["recipient@example.com"], msg.as_string())
server.quit()
```

**Double-check before sending:**
1. Does the body file contain MIME headers or boundaries? → ❌ Must be clean HTML/text only
2. Does the email need attachments? → ❌ Don't use `send_email.py` — use raw `smtplib` with `MIMEMultipart('mixed')`
3. Is the body file a complete .eml? → ❌ Wrong tool — use IMAP APPEND to Drafts or raw SMTP instead

### 🚨 Best practice: Reuse drafts instead of re-building

If you created a draft in Gmail (via IMAP APPEND to `[Gmail]/Drafts`) and it looks correct, **fetch it and send it as-is** via SMTP instead of re-building the MIME from scratch. This avoids accidentally corrupting the structure.

```python
import imaplib, smtplib, subprocess

# 1. Get credentials
pw = subprocess.run(
    ['security','find-generic-password','-a','your@email.com','-s','email-manager','-w'],
    capture_output=True, text=True
).stdout.strip()

# 2. Connect via IMAP and find the draft
m = imaplib.IMAP4_SSL("imap.gmail.com", 993)
m.login("your@email.com", pw)
m.select('"[Gmail]/Drafts"')
# Search by subject or date, then get the draft UID
s, d = m.uid('SEARCH', None, 'SUBJECT', 'Re: Subject')
draft_uid = d[0].split()[-1].decode()

# 3. Fetch the raw MIME of the draft
s, d = m.uid('FETCH', draft_uid, '(RFC822)')
raw_mime = d[0][1]  # complete, already well-formed with attachments
m.logout()

# 4. Send it as-is via SMTP (no re-construction!)
server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()
server.login("your@email.com", pw)
server.sendmail("your@email.com", ["recipient@example.com"], raw_mime)
server.quit()
print("✅ Draft fetched and sent as-is — no re-construction needed.")
```

✅ **Why this is better:**
- The draft was already validated visually in Gmail
- No risk of re-building the MIME structure incorrectly
- The attachment is guaranteed to be intact (you saw it in Gmail)
- Faster — one fetch + one SMTP send, no template manipulation

**Rule of thumb:** If you created a draft in Gmail and the user saw it there (or you visually verified it), **don't re-author it**. Just fetch and send.

### Save sent messages automatically

After sending, the agent saves the sent message to the contact's file so the style profile stays current:

```bash
# The agent does this automatically after sending
python3 -c "
import json
with open('contacts/messages/contact_file.json') as f:
    c = json.load(f)
c['messages'].insert(0, {'date': '...', 'subject': '...', 'body': '...'})
with open('contacts/messages/contact_file.json', 'w') as f:
    json.dump(c, f, ensure_ascii=False, indent=2)
"
```
