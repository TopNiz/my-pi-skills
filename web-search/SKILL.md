---
name: web-search
description: Perform advanced web searches using browser automation (Playwright). Search Google, DuckDuckGo, and other engines, extract structured results, and scrape page content.
allowed-tools: Bash(playwright-cli:*) Bash(npx:*)
---

# Web Search with Playwright

## Core Workflow Pattern (always follow this)

The key rule: **always inspect the page before acting**. Do not assume selectors like `e1` exist — they are snapshot-specific references that may not match the actual page.

### Step-by-step workflow

```bash
# 1. OPEN the browser (headless by default, add --headed if you get stuck)
playwright-cli open "https://lite.duckduckgo.com/lite/"

# 2. INSPECT — find the actual input field names/selectors on the page
playwright-cli --raw eval "() => [...document.querySelectorAll('input, textarea, select')].map(el => ({tag: el.tagName, id: el.id, name: el.name, type: el.type, placeholder: el.placeholder, className: el.className}))"
# └─ This tells you the real field names (e.g. name="q") instead of guessing "e1"

# 3. FILL in the search using the CORRECT selector (from step 2)
playwright-cli fill 'input[name="q"]' "your search query here"

# 4. SUBMIT
playwright-cli click 'input[type="submit"]'

# 5. WAIT for results to load
sleep 2

# 6. CHECK results — extract structured data
playwright-cli --raw eval "() => [...document.querySelectorAll('a')].filter(a => a.href?.startsWith('http') && !a.href.includes('duckduckgo.com')).slice(0,10).map(a => ({text: a.textContent?.trim(), href: a.href}))"

# 7. If you need to VISIT a result page, use goto
playwright-cli goto "https://example.com/page-to-read"
playwright-cli --raw eval "() => document.body.innerText.slice(0, 5000)"

# 8. When ALL searches are done, CLOSE the browser
playwright-cli close
```

### Using `--headed` when results don't make sense

If results are empty, selectors don't match, or the page looks different than expected:

```bash
# Open the browser VISUALLY so you (and the user) can see what's happening
playwright-cli open "https://lite.duckduckgo.com/lite/" --headed
```

The user will see the browser window and can help interpret what's wrong (e.g. "the search field has a different name", "there's a captcha", etc.).

### Multiple searches in one session

Keep the browser open and chain commands instead of opening/closing for each query:

```bash
playwright-cli open "https://lite.duckduckgo.com/lite/"

# First search
playwright-cli fill 'input[name="q"]' "first query"
playwright-cli click 'input[type="submit"]'
sleep 2
# ... extract results ...

# Second search (same page, new query)
playwright-cli fill 'input[name="q"]' "second query"
playwright-cli click 'input[type="submit"]'
sleep 2
# ... extract results ...

# Close only when done
playwright-cli close
```

### Anti-patterns to avoid

| ❌ Don't | ✅ Do |
|----------|------|
| `playwright-cli fill e1 "query"` without checking | First inspect the page with `--raw eval` to find the real field name |
| Opening and closing browser for every single search | Keep browser open, chain commands |
| Running a long script without checking intermediate results | Inspect after each step with `--raw eval` or `snapshot` |
| Assuming selectors work across different search engines | Each engine has different HTML structure — inspect first |

---

## Quick start

```bash
playwright-cli open https://lite.duckduckgo.com/lite/
playwright-cli --raw eval "() => [...document.querySelectorAll('input')].map(el => el.name)"
playwright-cli fill 'input[name="q"]' "your search query"
playwright-cli click 'input[type="submit"]'
sleep 2
playwright-cli --raw eval "() => [...document.querySelectorAll('a')].filter(a => a.href?.startsWith('http') && !a.href.includes('duckduckgo.com')).slice(0,10).map(a => ({text: a.textContent?.trim(), href: a.href}))"
playwright-cli close
```

---

## Search Engines & Strategies

### DuckDuckGo Lite (recommended — lightweight, no captcha)
URL: `https://lite.duckduckgo.com/lite/`
- Minimal HTML, fast loading
- No JavaScript rendering needed
- Input field: `input[name="q"]`

```bash
playwright-cli open https://lite.duckduckgo.com/lite/
playwright-cli fill 'input[name="q"]' "your search query"
playwright-cli click 'input[type="submit"]'
sleep 2
playwright-cli --raw eval "() => [...document.querySelectorAll('a')].filter(a => a.href?.startsWith('http') && !a.href.includes('duckduckgo.com')).slice(0,10).map(a => ({text: a.textContent?.trim(), href: a.href}))"
playwright-cli close
```

### DuckDuckGo HTML (alternative)
URL: `https://html.duckduckgo.com/html/`
- More structured result layout with CSS classes
- Input field: `input[name="q"]`

```bash
playwright-cli open https://html.duckduckgo.com/html/
playwright-cli fill 'input[name="q"]' "your search query"
playwright-cli click 'input[type="submit"]'
sleep 2
playwright-cli --raw eval "() => [...document.querySelectorAll('.result__title a')].slice(0,10).map(a => ({text: a.textContent?.trim(), href: a.href}))"
playwright-cli close
```

### Google (use with caution)
URL: `https://www.google.com/search?q=requête`
- May trigger captchas in automated mode
- Use `--headed` for manual captcha resolution if needed

```bash
playwright-cli open "https://www.google.com/search?q=your+search+query"
sleep 2
playwright-cli --raw eval "() => [...document.querySelectorAll('a')].filter(a => a.href?.startsWith('http') && !a.href.includes('google')).slice(0,10).map(a => ({text: a.textContent?.trim(), href: a.href}))"
playwright-cli close
```

### Bing (less aggressive bot detection)
URL: `https://www.bing.com/search?q=requête`

```bash
playwright-cli open "https://www.bing.com/search?q=your+search+query"
sleep 2
playwright-cli --raw eval "() => [...document.querySelectorAll('a')].filter(a => a.href?.startsWith('http') && !a.href.includes('bing')).slice(0,10).map(a => ({text: a.textContent?.trim(), href: a.href}))"
playwright-cli close
```

---

## Extracting page content (after finding a useful result)

### Get the main text of a page

```bash
playwright-cli goto "https://example.com/article"
sleep 2
playwright-cli --raw eval "() => document.querySelector('main')?.innerText || document.querySelector('article')?.innerText || document.body.innerText" > article-content.txt
```

### Get full page content for analysis

```bash
playwright-cli goto "https://example.com/documentation"
sleep 2
playwright-cli --raw eval "() => document.body.innerText.slice(0, 5000)" > page-content.txt
```

---

## Troubleshooting

### The page doesn't load correctly
```bash
playwright-cli open https://lite.duckduckgo.com/lite/ --headed
```

### Captcha or blocking
```bash
# 1. Try DuckDuckGo Lite (no captcha)
# 2. Use --headed and resolve manually
playwright-cli open "https://lite.duckduckgo.com/lite/" --headed
# 3. Add delays between actions
sleep 3
```

### CSS selectors don't match
```bash
# Snapshot captures the current page structure
playwright-cli snapshot --filename=page-state.yml
# Then inspect to find working selectors
playwright-cli --raw eval "() => document.body.innerHTML.slice(0, 3000)"
```
