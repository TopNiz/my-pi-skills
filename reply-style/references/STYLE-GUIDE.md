# 🎨 Style Analysis Guide

This reference describes the style dimensions the agent should analyze when examining your past messages and generating replies.

## Style Dimensions

### 1. Greeting / Opening

| Style | Examples |
|-------|----------|
| Formal | Bonjour, Cher/Chère, Dear Mr/Ms |
| Semi-formal | Bonjour [Prénom], Hi [Name] |
| Casual | Salut, Coucou, Hey, Hello |
| None | Starts directly with the message |

**For French:** Note whether you use "tu" or "vous" with the contact.

### 2. Sentence Structure

- **Short & punchy** — 5-15 words per sentence, gets straight to the point
- **Medium** — 15-30 words, balanced
- **Long & detailed** — 30+ words, explanatory, multiple clauses
- **Mixed** — Varies based on context

### 3. Punctuation Style

- **Minimal** — lowercase, few commas, no exclamation marks
- **Standard** — Proper punctuation, occasional exclamation
- **Expressive** — !! or !? , lots of commas and dashes — like this
- **Ellipsis-heavy** — Frequent use of... trailing thoughts...

### 4. Emoji / Emoticon Usage

- **Never** — No emojis in any message
- **Rare** — Once every few messages
- **Moderate** — 1-2 per message in casual contexts
- **Heavy** — Multiple emojis, replaces words with emojis

### 5. Paragraph Structure

- **Single paragraph** — One block of text
- **Multi-paragraph** — Separate thoughts into paragraphs
- **Bullet lists** — Uses lists for multiple items
- **Short lines** — Line breaks between each thought

### 6. Sign-off / Closing

| Style | Examples |
|-------|----------|
| Formal | Cordialement, Sincères salutations, Best regards, Sincerely |
| Semi-formal | Bien cordialement, Best, Cheers |
| Casual | A+, Merci, Thanks, À bientôt, See you |
| Just name | — Nizar, Nizar, /nizar |
| None | Ends with the message, no sign-off |

### 7. Formality Register

- **Formal** — "Je vous prie d'agréer...", "I would be grateful if..."
- **Professional** — "Could you please...", "I'd like to..."
- **Casual** — "Tu peux...", "Can you...", "Let me know"
- **Very casual** — "Tu fais ça quand tu peux", "Just ping me"

### 8. Language

- **French (fr)**
- **English (en)**
- **Arabic (ar)**
- **Mixed** — Code-switching between languages

### 9. Typical Message Length

- **Very short** — 1-2 sentences
- **Short** — 3-5 sentences / < 50 words
- **Medium** — 5-10 sentences / 50-150 words
- **Long** — 10+ sentences / 150+ words

### 10. Content Patterns

- **Question-heavy** — Asks lots of questions
- **Action-oriented** — States what you'll do / what needs to be done
- **Opinionated** — Gives clear opinions and preferences
- **Neutral** — Factual, information-sharing
- **Humorous** — Jokes, playful tone

---

## 11. Signature (CRITICAL)

Your signature **must match the language of the reply**. Two versions exist in both HTML and plain text.

> **Personal data**: Your real phone, email, and social links are stored in `config/signature.json` (gitignored).
> Copy `config/signature.example.json` to `config/signature.json` and fill in your details.
> The templates below use placeholders — the send script substitutes real values from the config.

### French signature — HTML

Uses your Chain-IT Apple Mail signature colors: **red `#d81e00`** and **grey `#797979` / `#424242`**. Preserve these colors and the Futura font when creating HTML drafts.

```html
<div id="AppleMailSignature">
  <meta charset="UTF-8">
  <div dir="auto" style="caret-color: rgb(0, 0, 0); color: rgb(0, 0, 0); letter-spacing: normal; text-align: start; text-indent: 0px; text-transform: none; white-space: normal; word-spacing: 0px; text-decoration-line: none; overflow-wrap: break-word; -webkit-nbsp-mode: space; line-break: after-white-space;">
    <div class="ApplePlainTextBody">
      <font face="Futura"><font size="4"><span style="font-style: normal;"><font color="#d81e00">Chain-</font><font color="#797979">IT&nbsp;</font><font color="#d81e00">. com</font></span></font><br></font>
    </div>
    <div class="ApplePlainTextBody">
      <font face="Futura">
        <font color="#424242"><b>{{NAME}}</b></font><br>
        <font color="#424242">{{TITLE}}</font><br><br>
        <font color="#424242">FR Mobile :</font><span class="Apple-tab-span" style="color: rgb(66, 66, 66); white-space: pre;">\t</span><font color="#424242">{{PHONE}}</font><br>
        <font color="#424242">eMail:<span class="Apple-tab-span" style="white-space: pre;">\t\t</span>{{EMAIL}}<br>Web:<span class="Apple-tab-span" style="white-space: pre;">\t\t</span>{{WEBSITE}}</font><br>
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

### French signature — Plain text

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

### English signature — HTML

Same Apple Mail styling, adapted for English.

```html
<div id="AppleMailSignature">
  <meta charset="UTF-8">
  <div dir="auto" style="caret-color: rgb(0, 0, 0); color: rgb(0, 0, 0); letter-spacing: normal; text-align: start; text-indent: 0px; text-transform: none; white-space: normal; word-spacing: 0px; text-decoration-line: none; overflow-wrap: break-word; -webkit-nbsp-mode: space; line-break: after-white-space;">
    <div class="ApplePlainTextBody">
      <font face="Futura"><font size="4"><span style="font-style: normal;"><font color="#d81e00">Chain-</font><font color="#797979">IT&nbsp;</font><font color="#d81e00">. com</font></span></font><br></font>
    </div>
    <div class="ApplePlainTextBody">
      <font face="Futura">
        <font color="#424242"><b>{{NAME}}</b></font><br>
        <font color="#424242">{{TITLE}}</font><br><br>
        <font color="#424242">Mobile:</font><span class="Apple-tab-span" style="color: rgb(66, 66, 66); white-space: pre;">\t</span><font color="#424242">{{PHONE}}</font><br>
        <font color="#424242">Email:<span class="Apple-tab-span" style="white-space: pre;">\t\t</span>{{EMAIL}}<br>Web:<span class="Apple-tab-span" style="white-space: pre;">\t\t</span>{{WEBSITE}}</font><br>
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

### English signature — Plain text

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

### Signature exceptions

- **Family/personal contacts:** Skip the full signature — just use first name or nothing (follow historical pattern)
- **Very short replies (1-2 words):** Signature optional, match what you've done before with that contact
- **Forwarded messages:** Keep the original email context, signature goes before the forwarded content
- **HTML vs plain text:** If replying to an HTML email, use HTML signature. If replying to plain text, use plain text signature.

---

## Style Profile Template

When generating a reply, the agent should construct a mental style profile like this:

```json
{
  "greeting": "Salut / Hey",
  "tu_vous": "tu",
  "sentence_length": "medium",
  "punctuation": "standard",
  "emoji": "moderate",
  "paragraphs": "single",
  "sign_off": "Merci — Nizar",
  "signature": "French (Chain-IT)",
  "formality": "casual",
  "language": "fr",
  "message_length": "short",
  "content_style": "action-oriented"
}
```

This gives the LLM a clear target to match.
