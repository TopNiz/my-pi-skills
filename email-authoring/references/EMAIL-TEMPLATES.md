# Email Layout Templates

## Required defaults for every email

Select the template from the verified sending account before creating or updating a draft:

| Sending account | HTML template, relative to this reference |
|---|---|
| `nizar@longhornip.com` | `../../email-manager/references/LONGHORNIP-EMAIL-TEMPLATE.html` |
| `nizar.ayed@chain-it.com` | `../../email-manager/references/CHAINIT-EMAIL-TEMPLATE.html` |

These defaults apply to new messages, replies, forwards, and short emails without tables. Do not use an unbranded fallback or select branding from the recipient. Explicit user requests for another layout take priority. The dedicated miXYtes layout remains available for user-identified miXYtes messages.

## Layout assembly

1. Read the selected HTML template in full.
2. Fill its placeholders. Escape text values with an HTML escaping function. Only `CONTENT_HTML` and `SIGNATURE_HTML` accept trusted HTML.
3. Keep the template's logo, colors, dimensions, spacing, header, and footer. Do not replace one account's brand with the other's.
4. Insert only the content requested by the user. Paragraphs and lists are sufficient for short messages. Do not add explanations, requests, or sections merely to fill the layout.
5. Use the account-specific signature in `STYLE-GUIDE.md`. Do not insert Chain-IT contact details into a Longhorn IP email.
6. Use inline styles for essential formatting. Media queries can supplement them.
7. Verify that no unresolved placeholders remain in the assembled HTML.

### Placeholder values

Both templates use `LANG`, `SUBJECT`, `TITLE`, `CONTENT_HTML`, and `SIGNATURE_HTML`.

The Chain-IT template also uses:
- `PREHEADER`: a short factual description of the message, without new claims.
- `FOOTER_TAGLINE`: the configured Chain-IT title for the message's selected language, or an explicitly supplied tagline.

A layout-only update preserves existing message wording and header values. Use the existing subject for the layout title when no separate title is supplied.

## Brand-specific content formatting

| Element | Longhorn IP | Chain-IT |
|---|---|---|
| Heading color | `#4d412c` | `#4A0D1B` |
| Accent | `#d9b626` | `#7A1A2E` |
| Body text | `#3c3a35` | `#1A1A1A` |
| Table header | `#6a593d`, white text | `#7A1A2E`, white text |
| Table stripe | `#faf7ef` | `#F7F5F3` |
| Table border | `#e6e1d5` | `#DCD3D3` |

Use real data tables only when the content needs them. Use column headers with `scope="col"`. Layout-only tables retain `role="presentation"`. Do not apply the former generic blue table theme over a branded template.

## Logos and MIME structure

- Longhorn IP: preserve the existing remote logo URL in its template. Do not silently replace it with another image. Remote-image display depends on the recipient's email settings.
- Chain-IT: embed `../../email-manager/references/chainit-web-logo.png` in the HTML `multipart/related` branch with `Content-ID: <chainit-web-logo>` and inline disposition. The HTML uses `cid:chainit-web-logo`. Do not attach it as a regular file.
- Include both plain text and HTML in `multipart/alternative`. The plain-text fallback must contain the same message content and signature, without HTML markup.
- If files are attached, use an outer `multipart/mixed` and preserve all attachments during updates.
- Check saved MIME and image references after Gmail draft creation or update. A successful API response alone does not establish layout fidelity.

## Draft and send rules

Create drafts in the selected Gmail account, preserving reply threading. Never send without explicit user confirmation. After approval, prefer sending the exact saved draft through the Gmail API, not a desktop composer that may rewrite the HTML.

These instructions control presentation only. They do not define expression style, tone, greeting, vocabulary, sentence structure, or contact-specific phrasing.
