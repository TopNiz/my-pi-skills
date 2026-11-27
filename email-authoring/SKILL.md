---
name: email-authoring
description: Create HTML email drafts with the sending account's required branded layout and signature. Longhorn IP and Chain-IT templates apply by default to all emails, including short replies. No contact profiling or expression-style system.
allowed-tools: read write edit bash
---

# Email Layout and Drafts

This skill controls HTML layout, branding, signatures, and draft preparation only.
It does not prescribe expression style, tone, vocabulary, greetings, sentence structure, or alternative phrasings.
Use the user's requested wording and content. Do not rewrite content merely to fit a layout.

## Required default templates

Choose branding from the verified sending account, not the recipient, current workspace, or a default signature file.

| Sending account | Required default layout | Signature |
|---|---|---|
| `nizar@longhornip.com` | `../email-manager/references/LONGHORNIP-EMAIL-TEMPLATE.html` | Longhorn IP |
| `nizar.ayed@chain-it.com` | `../email-manager/references/CHAINIT-EMAIL-TEMPLATE.html` | Chain-IT |

These defaults apply to every new email, reply, forward, and draft update, including short messages without tables.
Do not substitute plain HTML, a generic layout, or the other account's branding.
Do not omit the template because the message is short or informal.
A user's explicit request for a different layout takes priority.
For an explicitly identified miXYtes message, retain the dedicated layout and signature documented in `../email-manager/SKILL.md`.
For any other sending account or alias whose branding is not established, ask instead of guessing.

Read these references before preparing an email:
- The selected account's HTML template, in full.
- `references/EMAIL-TEMPLATES.md`: layout and MIME assembly rules.
- `references/STYLE-GUIDE.md`: layout-only signature reference, retained at this path for compatibility.

## No expression-style system

- Do not read contact profiles, contact indexes, or sent-message histories to imitate writing.
- Do not run `scripts/fetch_sent.py` or `scripts/rebuild_contacts.py` for authoring.
- Do not build, update, or save expression-style profiles or learning examples.
- Do not infer tone or phrasing from contact categories.
- Do not require multiple wording options, language matching, standard greetings, or a fixed sign-off.
- Follow the user's instructions for content, language, wording, and length.
- Existing profile data and legacy scripts are not part of the active workflow. Do not delete or modify them without separate permission.

## Draft workflow

1. Identify the sending account and intended recipients. For a reply, inspect the original message's headers and thread. Do not add recipients without instruction.
2. Prepare only the content requested by the user.
3. Read and apply the account-specific template and signature. Preserve the message's wording during layout-only updates.
4. Escape text inserted into HTML placeholders. Insert only trusted HTML into `CONTENT_HTML` and `SIGNATURE_HTML`.
5. Assemble `multipart/alternative` with HTML and a matching plain-text fallback. Place embedded logo images in a `multipart/related` HTML branch using the template's Content-ID.
6. Use the Gmail API to create the draft in the selected account. For an existing draft, update only the uniquely identified draft being managed.
7. Preserve reply threading with `threadId`, `In-Reply-To`, and `References`. Preserve attachments when updating an existing draft.
8. Inspect the saved draft: account, recipients, wording, branding, signature, placeholders, embedded image references, and attachments.
9. Report that the draft is ready and has not been sent.

## Sending safeguards

- A draft request is not permission to send. Never execute a send without explicit user confirmation.
- After confirmation, send the exact approved Gmail draft through the Gmail API. Do not rebuild it or route it through Apple Mail or another composer that can alter the HTML.
- Do not promise identical rendering in every email client.
- Do not log credentials, authorization links, or other secrets.
- Use the account-specific authentication described in `../email-manager/SKILL.md`. Do not install dependencies, migrate credentials, or change authentication configuration as part of authoring.
