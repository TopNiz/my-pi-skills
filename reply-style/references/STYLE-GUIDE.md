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

### French signature — Plain text

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

### English signature — HTML

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
  <font color="#253887">Facebook :&nbsp;<a href="{{FACEBOOK}}" style="color: rgb(37, 56, 135);">{{FACEBOOK}}</a></font><br>
  <font color="#253887">Twitter :&nbsp;<a href="{{TWITTER}}" style="color: rgb(37, 56, 135);">{{TWITTER}}</a></font><br>
  <font color="#253887">Web :&nbsp;<a href="{{WEBSITE}}" style="color: rgb(37, 56, 135);">{{WEBSITE}}</a></font>
  <br><br>
  <font color="#999" style="font-size: 11px;">🤖 AI generated message and approved by him ✨</font>
</div>
```

### English signature — Plain text

```
{{NAME}}
{{TITLE}}

Tel: {{PHONE}}
Email: {{EMAIL}}
Facebook : {{FACEBOOK}}
Twitter : {{TWITTER}}
{{WEBSITE}}
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
  "signature": "French (Digital Coach)",
  "formality": "casual",
  "language": "fr",
  "message_length": "short",
  "content_style": "action-oriented"
}
```

This gives the LLM a clear target to match.
