---
name: web-search
description: Perform advanced web searches using browser automation (Playwright). Search Google, DuckDuckGo, and other engines, extract structured results, and scrape page content.
allowed-tools: Bash(playwright-cli:*) Bash(npx:*)
---

# Web Search with Playwright

## Golden Rules

1. **`--headed` by default.** Always open the browser in headed mode to avoid captchas (DuckDuckGo, Bing, and Google all block headless browsers aggressively).
2. **One step at a time.** Execute ONE action, inspect the result, then decide what to do next. Never batch multiple steps in a single bash command or playwright eval.
3. **Check after every step.** After opening a page: verify it loaded. After filling a form: verify the field has the right value. After clicking: verify the page changed. After extracting results: verify they're meaningful.
4. **If results are unexpected, STOP and investigate.** Don't blindly continue. Check the page content, check for captchas, check if selectors still match.
5. **If stuck after 2-3 attempts, ask the user.** They can see the headed browser window and help resolve captchas, selectors, or site-specific issues.
6. **Close the browser when done.** Always run `playwright-cli close` immediately after the search/browsing task finishes, even if the user did not explicitly ask. Do not leave headed browser windows open.

---

## Step-by-Step Workflow

### Step 1 — Open the browser (headed)

```bash
playwright-cli open "https://lite.duckduckgo.com/lite/" --headed
```

**Check:** The command outputs `Browser 'default' opened`. If it shows an error, stop and investigate.

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

### Step 10 — Close the browser — mandatory final step

Always close the browser after extracting the final results or finishing the requested browsing task:

```bash
playwright-cli close
```

**Check:** `Browser 'default' closed` is shown. If it errors because no browser is open, that's fine — the goal is to ensure no headed browser window is left open.

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
- Most aggressive with captchas — use `--headed` and expect user help
- Results: `a[jsname]` or `div.yuRUbf a`

### Bing (fallback if DDG fails)
```
https://www.bing.com/search?q=your+query
```
- Less aggressive than Google but still blocks headless
- Results: `li.b_algo h2 a`

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
| Restart browser for every search | Keep browser open, chain searches |
| Ignore empty results | Stop, inspect the page, find why |
| Keep trying the same failing approach >3 times | Ask the user for help |
| Forget to close the browser | Always close with `playwright-cli close` as the mandatory final step of every search/browsing task |

---

## Debugging checklist when results are empty

1. Check page content: `playwright-cli --raw eval "() => document.body.innerText.slice(0, 1000)"`
2. Check for captcha or blocking messages
3. Check the actual HTML: `playwright-cli --raw eval "() => document.body.innerHTML.slice(0, 3000)"`
4. Check if selectors changed: `playwright-cli --raw eval "() => [...document.querySelectorAll('a, input, button')].map(el => ({tag: el.tagName, id: el.id, class: el.className, text: el.textContent?.trim().slice(0,50)}))"`
5. Try a different search engine
6. If still stuck after 2-3 attempts → **ask the user**
