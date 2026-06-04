---
name: reply-style
description: Answer messages by imitating your writing style. Fetches your sent emails from IMAP, builds per-contact style profiles, and drafts replies in your voice — matching the language and tone you use with each person. Supports email, Slack, LinkedIn, SMS, and any messaging platform.
allowed-tools: read write edit bash
---

# 🗣️ Reply Style Skill

Drafts replies to messages by learning **your personal writing style per contact**. Instead of generic AI-sounding responses, get replies that sound like *you*.

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

Uses your Apple Mail signature colors: **blue `#253887`** and **orange `#ff9300`**.

```html
<div style="font-family: Helvetica; font-size: 12px; color: rgb(0, 0, 0);">
  <span style="font-size: 16px;">
    <b><font style="color: rgb(37, 56, 135);">Upgrade-code .&nbsp;</font><font color="#ff9300">org</font></b>
  </span><br>
  <b style="color: rgb(37, 56, 135);">{{NAME}}</b><br>
  <font color="#253887">{{TITLE}}</font><br>
  <br>
  <font color="#253887">FR Mobile :&nbsp;<span>{{PHONE}}</span></font><br>
  <font color="#253887">eMail :&nbsp;<a href="mailto:{{EMAIL}}" style="color: rgb(37, 56, 135);">{{EMAIL}}</a></font><br>
  <font color="#253887">Facebook :&nbsp;<a href="{{FACEBOOK}}" style="color: rgb(37, 56, 135);">{{FACEBOOK}}</a></font><br>
  <font color="#253887">Twitter :&nbsp;<a href="{{TWITTER}}" style="color: rgb(37, 56, 135);">{{TWITTER}}</a></font><br>
  <font color="#253887">Web :&nbsp;<a href="{{WEBSITE}}" style="color: rgb(37, 56, 135);">{{WEBSITE}}</a></font>
  <br><br>
  <font color="#999" style="font-size: 11px;">🤖 Message généré par IA et approuvé par lui ✨</font>
</div>
```

#### French signature — Plain text (for French plain text replies)

```
{{NAME}}
{{TITLE}}

FR Mobile :	{{PHONE}}
eMail:		{{EMAIL}}
Facebook : 	{{FACEBOOK}}
Twitter : 		{{TWITTER}}
Web:		{{WEBSITE}}
🤖 Message généré par IA et approuvé par lui ;-)
```

#### English signature — HTML (for all English HTML replies)

Same Apple Mail styling, adapted for English.

```html
<div style="font-family: Helvetica; font-size: 12px; color: rgb(0, 0, 0);">
  <span style="font-size: 16px;">
    <b><font style="color: rgb(37, 56, 135);">Upgrade-code&nbsp;</font><font color="#ff9300">.org</font></b>
  </span><br>
  <b style="color: rgb(37, 56, 135);">{{NAME}}</b><br>
  <font color="#253887">{{TITLE}}</font><br>
  <br>
  <font color="#253887">Tel :&nbsp;<span>{{PHONE}}</span></font><br>
  <font color="#253887">Email :&nbsp;<a href="mailto:{{EMAIL}}" style="color: rgb(37, 56, 135);">{{EMAIL}}</a></font><br>
  <font color="#253887">Web :&nbsp;<a href="{{WEBSITE}}" style="color: rgb(37, 56, 135);">{{WEBSITE}}</a></font>
  <br><br>
  <font color="#999" style="font-size: 11px;">🤖 AI generated message and approved by him ✨</font>
</div>
```

#### English signature — Plain text (for English plain text replies)

```
{{NAME}}
{{TITLE}}

Tel: {{PHONE}}
Email: {{EMAIL}}
{{WEBSITE}}
🤖 AI generated message and approved by him ;-)
```

> **Rule:** If the reply is in French → use the French signature. If the reply is in English → use the English signature. The language of the message dictates the signature language, regardless of the recipient.

> **Format rule:** If replying to an HTML-formatted incoming email → use the HTML signature. If replying to a plain text incoming email → use the plain text signature. When in doubt, use plain text.

> **Short replies (1-2 sentences):** For very short replies (like "Bien reçu !" or "I'm there"), the signature is optional — match what you've done historically with that contact.

> **Family/personal contacts:** For family members (like Sonia, category: family), you typically don't include a full signature. Just your first name or nothing. Follow the pattern from your past messages with that person.

8. **Draft → Confirm → Send** — Never send a message directly. Always:
   - **Step 1 — Draft**: Present the reply option(s) to the user
   - **Step 2 — Confirm**: Wait for the user to approve, request changes, or choose an option
   - **Step 3 — Send**: Only after the user explicitly confirms ("Send it", "Yes", "Go ahead"), proceed to send the message

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
    └── STYLE-GUIDE.md             ← Reference for style analysis criteria
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
