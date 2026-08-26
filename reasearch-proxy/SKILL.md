---
name: reasearch-proxy
description: Use Université de Lorraine proxied access (bases-doc / EZproxy / CAS) to access, search, and download academic/research articles from subscribed databases such as ScienceDirect, Nature, Wiley, Springer, Oxford, etc. Includes PDF download from Chrome PDF viewer with Playwright.
allowed-tools: Bash(playwright-cli:*) Bash(file:*) Bash(ls:*) Bash(mkdir:*) Bash(test:*) Bash(cp:*) Bash(mv:*) Bash(rm:*)
---

# Research Proxy — Université de Lorraine

Use this skill when the user wants bibliographical research and source downloads through Université de Lorraine subscriptions.

## Core principle

Université de Lorraine uses a `bases-doc.univ-lorraine.fr` proxy / EZproxy-style access path with CAS login.

Never ask for or display the user's university password. Let the user authenticate manually in the headed browser window.

## Mandatory workspace browser profile

Before opening or using Playwright, inspect `playwright-cli list` and the directories under `$PWD/.playwright/profiles`.

- **Exactly one profile:** use it exclusively. Its directory basename must also be the Playwright session name. Reuse its profile-backed session if open, or reopen it headed with `--profile="$PWD/.playwright/profiles/<profile-name>"`.
- **No profile:** create the first persistent workspace profile by opening headed with `--profile="$PWD/.playwright/profiles/<session-name>"`; use the same stable, workspace-specific name for the session and directory.
- **More than one profile:** ask the user which to use; never guess or create another profile.
- Never use `default`, an in-memory session, or a task-named session without `--profile`. Treat sessions not backed by the current workspace profile directory as outside/ambiguous; do not use, modify, or close them without explicit user identification.

Every `playwright-cli` command below must be scoped as `-s=<profile-name>`, where `<profile-name>` is the selected profile basename. Leave the persistent session open unless the user explicitly asks to close that identified session.

## Important URLs and patterns

### Official proxy entrypoint

Use this format to send a publisher URL through the UL proxy:

```text
http://bases-doc.univ-lorraine.fr/login?url=<URL-ENCODED-PUBLISHER-URL>
```

Example pattern:

```text
http://bases-doc.univ-lorraine.fr/login?url=https%3A%2F%2Fwww.sciencedirect.com%2Fscience%2Farticle%2Fpii%2F...
```

### Host-suffix pattern

UL also supports transforming publisher URLs by appending the proxy suffix to the hostname:

```text
http://www.nature.com.bases-doc.univ-lorraine.fr/
```

For ScienceDirect, use `http://` first to avoid certificate mismatch errors:

```text
http://www.sciencedirect.com.bases-doc.univ-lorraine.fr/science/article/pii/<PII>
```

The proxy may redirect this to a hyphenated proxied HTTPS hostname such as:

```text
https://www-sciencedirect-com.bases-doc.univ-lorraine.fr/science/article/pii/<PII>
```

Do **not** start directly with:

```text
https://www.sciencedirect.com.bases-doc.univ-lorraine.fr/...
```

That can produce certificate common-name errors.

### Do not confuse with the UL HTTP network proxy

UL also documents a generic HTTP proxy (`proxy.infra.univ-lorraine.fr:3128`, PAC files). This is for network/browser proxy configuration and is not the preferred workflow for accessing subscribed article PDFs. For research sources, use `bases-doc.univ-lorraine.fr`.

## Authentication workflow

1. Open a headed browser:

```bash
playwright-cli -s=<profile-name> open --headed \
  --profile="$PWD/.playwright/profiles/<profile-name>" \
  "http://bases-doc.univ-lorraine.fr/login?url=<encoded-url>"
```

2. If redirected to CAS (`auth.univ-lorraine.fr`), stop and ask the user to log in manually.

3. After the user says they are logged in, inspect the current page:

```bash
playwright-cli -s=<profile-name> --raw eval "() => ({url: location.href, title: document.title, text: document.body.innerText.slice(0, 1000)})"
```

4. If authentication lands on the UL resource menu rather than the target article, navigate manually to the proxied article URL using the host-suffix pattern.

Example for ScienceDirect:

```bash
playwright-cli -s=<profile-name> goto "http://www.sciencedirect.com.bases-doc.univ-lorraine.fr/science/article/pii/<PII>"
```

## ScienceDirect article workflow

1. Navigate to the proxied article page:

```bash
playwright-cli -s=<profile-name> goto "http://www.sciencedirect.com.bases-doc.univ-lorraine.fr/science/article/pii/<PII>"
```

2. Verify the article page loaded:

```bash
playwright-cli -s=<profile-name> --raw eval "() => ({url: location.href, title: document.title})"
```

3. Find the primary PDF link:

```bash
playwright-cli -s=<profile-name> --raw eval "() => [...document.querySelectorAll('a,button')].map((el,i)=>({i,tag:el.tagName,text:el.innerText?.trim().slice(0,100), href:el.href || '', aria:el.getAttribute('aria-label') || '', title:el.getAttribute('title') || ''})).filter(x=>/pdf|download|full/i.test([x.text,x.href,x.aria,x.title].join(' '))).slice(0,20)"
```

4. Click the first article-level PDF link:

```bash
playwright-cli -s=<profile-name> click 'a[href*="/pdfft"] >> nth=0'
```

This usually opens a new tab displaying the PDF in Chrome's PDF viewer.

## Saving PDFs displayed in Chrome's PDF viewer

When a PDF opens in Chrome's built-in viewer, **do not use `playwright-cli pdf`**. That saves a printout of the viewer/page, not the original article PDF.

Use the viewer's download button and capture Playwright's `download` event.

1. Select the PDF tab:

```bash
playwright-cli -s=<profile-name> tab-list
playwright-cli -s=<profile-name> tab-select <pdf-tab-index>
```

2. Take a screenshot if needed to locate the download icon in the toolbar:

```bash
playwright-cli -s=<profile-name> screenshot --filename=.playwright-cli/pdf-viewer.png
```

3. Trigger the viewer download button and save the real PDF:

```bash
playwright-cli -s=<profile-name> --raw run-code "async page => { const out = '902-academic/article-main.pdf'; const downloadPromise = page.waitForEvent('download', { timeout: 20000 }); await page.mouse.click(1095, 28); const download = await downloadPromise; await download.saveAs(out); return {saved: out, suggested: download.suggestedFilename()}; }"
```

4. Verify the output:

```bash
file "902-academic/article-main.pdf" && ls -lh "902-academic/article-main.pdf"
```

Expected: `PDF document`, with realistic size (often multiple MB). If it says HTML, the file is not the actual PDF.

### Notes on coordinates

The click coordinates depend on the browser size and toolbar position. In a typical Chrome PDF viewer at 1200px width, the download icon is near `(1095, 28)`. If this fails, take a screenshot and adjust the coordinates.

## Common pitfalls

- `playwright-cli pdf --filename=...` is for printing an HTML page to PDF. It is **not** for downloading an already-displayed PDF.
- Direct `curl` of signed ScienceDirect PDF URLs may return HTML or fail because the request lacks the browser/session context.
- Playwright request/fetch may also fail on proxied or signed URLs; for Chrome PDF viewer, the most reliable approach is viewer download + `download.saveAs(...)`.
- Direct `https://publisher.com.bases-doc.univ-lorraine.fr/...` may fail with a certificate error. Start with `http://publisher.com.bases-doc.univ-lorraine.fr/...` and let the proxy redirect.

## Good file naming

Save sources with stable names that include reference ID and publisher/article ID:

```text
902-academic/A1-sciencedirect-S2666188825001388-main.pdf
902-academic/A2-nature-s41467-024-50088-4.pdf
```

## Cleanup

Only delete failed artifacts when the user explicitly confirms. Keep the verified PDF.
