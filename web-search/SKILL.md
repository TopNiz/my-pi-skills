---
name: web-search
description: Perform advanced web searches using browser automation (Playwright). Search Google, DuckDuckGo, and other engines, extract structured results, and scrape page content.
allowed-tools: Bash(playwright-cli:*) Bash(npx:*)
---

# Web Search with Playwright

## Golden Rules

1. **Use only workspace-local sessions.** Before starting a browser, list and separate workspace-owned sessions/profiles from outside or ambiguous sessions (see Step 0). Reuse only a suitable workspace session/profile; do not attach to, modify, or close sessions that do not clearly belong to the current workspace.
2. **`--headed` MANDATORY for search/scraping — headless only with explicit user confirmation.** Always open the browser in headed mode: DuckDuckGo, Bing, Google, and most scraping-averse sites (Cloudflare-protected, LinkedIn, OpenAI Help Center, EZproxy/ProQuest, ScienceDirect, captcha-walled pages…) block headless browsers aggressively. If headless seems necessary or is requested, **ask the user first and wait for a clear affirmative answer** — never run headless silently. Detection signals: "Just a moment...", HTTP 403, "Enable JavaScript and cookies to continue", captcha text, login walls, rate-limit pages.
3. **One step at a time.** Execute ONE action, inspect the result, then decide what to do next. Never batch multiple steps in a single bash command or playwright eval.
4. **Check after every step.** After opening a page: verify it loaded. After filling a form: verify the field has the right value. After clicking: verify the page changed. After extracting results: verify they're meaningful.
5. **If results are unexpected, STOP and investigate.** Don't blindly continue. Check the page content, check for captchas, check if selectors still match.
6. **If stuck after 2-3 attempts, ask the user.** They can see the headed browser window and help resolve captchas, selectors, or site-specific issues.
7. **Close only sessions you created.** Close ad-hoc search sessions only if this agent/session created them. Do not close user-requested persistent workspace sessions or any outside/ambiguous sessions unless the user explicitly identifies them.

---

## Step-by-Step Workflow

### Step 0 — Identify workspace-local sessions; ignore outside sessions

Always separate current-workspace sessions/profiles from outside or ambiguous sessions before opening, attaching to, or closing anything.

```bash
# 1) List all currently running playwright-cli sessions (may include other workspaces)
playwright-cli list

# 2) List current-workspace persistent profile names only
find "$PWD/.playwright/profiles" -maxdepth 1 -mindepth 1 -type d -exec basename {} \; 2>/dev/null | sort

# 3) Separate open sessions by ownership convention:
#    workspace-owned = open session name matches a profile under $PWD/.playwright/profiles
#    outside/ambiguous = every other open session; do not touch without explicit user confirmation
OPEN_SESSIONS=$(playwright-cli list 2>/dev/null | awk '/^- /{gsub(":$","",$2); print $2}' | sort)
LOCAL_PROFILES=$(find "$PWD/.playwright/profiles" -maxdepth 1 -mindepth 1 -type d -exec basename {} \; 2>/dev/null | sort)
printf '%s\n' "Workspace-owned open sessions:"
comm -12 <(printf '%s\n' "$OPEN_SESSIONS") <(printf '%s\n' "$LOCAL_PROFILES")
printf '%s\n' "Outside or ambiguous open sessions (do not touch):"
comm -23 <(printf '%s\n' "$OPEN_SESSIONS") <(printf '%s\n' "$LOCAL_PROFILES")
```

If a suitable workspace-owned named session is open, use it:

```bash
playwright-cli -s=<session-name> snapshot
```

If a suitable workspace profile exists but is not open, reopen it headed using the matching session name:

```bash
playwright-cli -s=<session-name> open --headed --profile="$PWD/.playwright/profiles/<session-name>" "https://lite.duckduckgo.com/lite/"
```

If no workspace profile/session exists and a temporary session is needed, create a clearly named workspace session instead of `default` when possible:

```bash
playwright-cli -s=web-search open --headed "https://lite.duckduckgo.com/lite/"
```

Never print saved cookies, storage-state, localStorage, or profile contents.

### Step 1 — Open the browser (headed)

> ⛔ **HARD RULE:** `--headed` is mandatory for search/scraping. Headless only after the user explicitly confirms it. If in doubt → ask the user first.

Only do this if no suitable workspace session/profile exists. Prefer a clearly named session for this workspace/task.

```bash
playwright-cli -s=web-search open "https://lite.duckduckgo.com/lite/" --headed
```

If the CLI forces `default`, treat it as disposable only if this agent/session created it. Do not reuse or close an existing `default` session unless you created it or the user explicitly confirms it is yours.

**Check:** The command outputs that the chosen browser session opened. If it shows an error, stop and investigate.

### Step 2 — Inspect the page

```bash
playwright-cli --raw eval "() => document.body.innerText.slice(0, 1000)"
```

**Check for:**
- ✅ Normal page content (search field, title, etc.)
- ❌ Captcha messages ("Unfortunately, bots use DuckDuckGo too", "Please solve this challenge", etc.)
- ❌ Error pages, blank pages, redirects

**If there's a captcha:** Ask the user — they can see the headed window and solve it manually.

### Step 3 — Find the search field

```bash
playwright-cli --raw eval "() => [...document.querySelectorAll('input, textarea, select')].map(el => ({tag: el.tagName, id: el.id, name: el.name, type: el.type, placeholder: el.placeholder, className: el.className}))"
```

**Check:** Verify the search input field is found (e.g. `name="q"`). If no fields found, inspect the page HTML instead.

### Step 4 — Fill the search query

```bash
playwright-cli fill 'input[name="q"]' "your search query here"
```

**Check:** No errors means the field was found and filled.

### Step 5 — Submit

```bash
playwright-cli click 'input[type="submit"]'
```

**Check:** The page title should now include your search query. Wait 2-3 seconds for results.

### Step 6 — Wait and check for captcha

```bash
sleep 3
playwright-cli --raw eval "() => document.body.innerText.slice(0, 1000)"
```

**Check:**
- ✅ Results page with search results
- ❌ Captcha challenge ("Select all squares containing a duck", etc.)

**If captcha appeared:** Ask the user to solve it visually in the headed window.

### Step 7 — Extract results

```bash
playwright-cli --raw eval "() => [...document.querySelectorAll('a')].filter(a => a.href?.startsWith('http') && !a.href.includes('duckduckgo.com')).slice(0,10).map(a => ({text: a.textContent?.trim(), href: a.href}))"
```

**Check:**
- ✅ 5-10 results with titles and URLs
- ❌ Empty array `[]` — means selectors don't match or results didn't load
- ❌ Fewer than 3 results — might be captcha or no results

**If results are empty:** Check the page HTML to find the actual result structure:
```bash
playwright-cli --raw eval "() => document.body.innerHTML.slice(0, 3000)"
```

### Step 8 — Visit a result (optional)

```bash
playwright-cli goto "https://example.com/result-page"
sleep 2
playwright-cli --raw eval "() => document.body.innerText.slice(0, 5000)"
```

**Check:** The page content loaded correctly.

### Step 9 — Save a PDF displayed in Chrome's PDF viewer (when needed)

If a PDF opens in Chrome's built-in PDF viewer, **do not use `playwright-cli pdf`**. That prints/saves the viewer page, not the original PDF. Use the viewer's download button and capture Playwright's `download` event.

1. Select the tab containing the displayed PDF:

```bash
playwright-cli tab-list
playwright-cli tab-select <pdf-tab-index>
```

2. If needed, take a screenshot to locate the PDF viewer toolbar/download button:

```bash
playwright-cli screenshot --filename=.playwright-cli/pdf-viewer.png
```

3. Trigger the viewer download button and save the actual downloaded file:

```bash
playwright-cli --raw run-code "async page => { const out = 'path/to/article.pdf'; const downloadPromise = page.waitForEvent('download', { timeout: 20000 }); await page.mouse.click(1095, 28); const download = await downloadPromise; await download.saveAs(out); return {saved: out, suggested: download.suggestedFilename()}; }"
```

4. Verify the saved file is a real PDF:

```bash
file path/to/article.pdf && ls -lh path/to/article.pdf
```

**Notes:**
- The click coordinates depend on the browser size. Use the screenshot to adjust them.
- This is especially useful for ScienceDirect/EZproxy PDFs that render correctly in the browser but fail when fetched directly with `curl`.
- Alternative approaches documented online include Playwright `page.waitForEvent('download')` + `download.saveAs(...)`; direct `fetch()`/request API may fail on proxied or signed PDF URLs.

### Step 10 — Close disposable browsers; preserve persistent workspace sessions

After extracting the final results or finishing the requested browsing task, close only the ad-hoc/disposable session that this agent/session created:

```bash
playwright-cli -s=web-search close
```

If you created a different named disposable session, close that exact session name. If the session is `default`, close it only if you know this agent/session created it; otherwise ask first.

If you reused a user-requested persistent workspace session (for example `-s=nespresso` with `.playwright/profiles/nespresso`), leave it open unless the user explicitly asks to close it. Never close outside/ambiguous sessions from `playwright-cli list`.

**Check:** The output names the exact session closed. If it errors because no such browser is open, that's fine.

---

## Search Engines & Strategies

### DuckDuckGo Lite (recommended first attempt)
```
https://lite.duckduckgo.com/lite/
```
- Minimal HTML, fast loading
- Prone to captchas in headless mode → always use `--headed`
- Input field: `input[name="q"]`
- Results: `a` tags with href starting with `http`

### DuckDuckGo HTML (alternative if Lite is blocked)
```
https://html.duckduckgo.com/html/
```
- More structured results with CSS classes
- Same field: `input[name="q"]`
- Results: `.result__title a`

### Google (fallback)
```
https://www.google.com/search?q=your+query
```
- Most aggressive with captchas — `--headed` always (never headless without explicit user confirmation)
- Results: `a[jsname]` or `div.yuRUbf a`

### Bing (fallback if DDG fails)
```
https://www.bing.com/search?q=your+query
```
- Less aggressive than Google but still blocks headless — `--headed` always
- Results: `li.b_algo h2 a`

**Scraping-averse sites (headless requires explicit user confirmation):** Google, Bing, DuckDuckGo, LinkedIn, Facebook, Instagram, OpenAI Help Center, Cloudflare-protected sites, EZproxy/ProQuest, ScienceDirect, captcha/login-walled pages. Detect via: "Just a moment..." title, HTTP 403, "Enable JavaScript and cookies to continue", captcha text, rate-limit pages.

**If one engine blocks you:** Try another. If all block, ask the user to solve the captcha in the headed window.

---

## Captcha Handling

If any of these appear in the page content:

- "Unfortunately, bots use DuckDuckGo too"
- "Please complete the following challenge"
- "Select all squares containing a"
- "One last step — Please solve the challenge"
- CAPTCHA / reCAPTCHA

**Do NOT continue blindly.** Stop and tell the user. They can see the headed browser window and solve it. After they solve it, re-check the page and continue.

---

## Anti-patterns

| ❌ Don't | ✅ Do |
|----------|------|
| Batch open + fill + submit + extract in one bash command | One action per bash command, inspect between each |
| Assume selectors like `e1` or `#r1-0` work | Inspect the actual page structure first |
| Assume no captcha | Check page content after every navigation |
| Restart browser for every search | Reuse an existing workspace session/profile when available |
| Ignore empty results | Stop, inspect the page, find why |
| Keep trying the same failing approach >3 times | Ask the user for help |
| Close a persistent workspace session without being asked | Close only disposable sessions; preserve user-requested persistent sessions |

---

## Debugging checklist when results are empty

1. Check page content: `playwright-cli --raw eval "() => document.body.innerText.slice(0, 1000)"`
2. Check for captcha or blocking messages
3. Check the actual HTML: `playwright-cli --raw eval "() => document.body.innerHTML.slice(0, 3000)"`
4. Check if selectors changed: `playwright-cli --raw eval "() => [...document.querySelectorAll('a, input, button')].map(el => ({tag: el.tagName, id: el.id, class: el.className, text: el.textContent?.trim().slice(0,50)}))"`
5. Try a different search engine
6. If still stuck after 2-3 attempts → **ask the user**
