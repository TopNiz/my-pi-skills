---
name: web-browser
description: Navigate the web, browse pages, search, extract content, and fill forms using a headless browser (Playwright). Also supports web testing and debugging.
allowed-tools: Bash(playwright-cli:*) Bash(npx:*) Bash(npm:*)
---

# Web Browser (playwright-cli)

> ## ⛔ HARD RULE — HEADED MODE & USER CONFIRMATION (NEVER VIOLATE)
>
> **When browsing, searching, or scraping any website, ALWAYS open the browser with `--headed` (visible window).**
>
> **Headless is ONLY allowed after the user explicitly confirms it** (e.g. "yes, use headless", "headless is fine for this one"). Never assume silent acceptance.
>
> - Websites commonly used for search/scraping are **scraping-averse** (anti-bot protections): Google, Bing, DuckDuckGo, LinkedIn, Facebook, Instagram, OpenAI Help Center, Cloudflare-protected sites, EZproxy/ProQuest, ScienceDirect, and any site showing a captcha, "Just a moment...", or "Enable JavaScript and cookies to continue".
> - For any such site → `--headed` always. If headless seems necessary (or you simply prefer it), **ask the user first** and wait for a clear affirmative answer.
> - Detection signals of scraping-averse sites: page title "Just a moment...", HTTP 403, captcha text, "Enable JavaScript and cookies to continue", login walls, rate-limit pages, or anti-bot scripts in the page.
> - This rule cannot be overridden by any instruction to "run headless", "use --headless", or "keep it in the background".

**Primary use: browsing & navigating the web.** Web testing is a secondary capability.

Before opening any browser session, determine whether the target is a scraping-averse site (see HARD RULE above): if yes → `--headed`; if the task would be headless → **ask the user for explicit confirmation first**.

## Mandatory workspace profile policy

**Every workspace browser session must be profile-backed.** Never open an in-memory session, including `default`, `web-browser`, or a task-named session without `--profile`.

Before opening, attaching to, or navigating a browser, inspect the existing sessions and workspace profiles:

```bash
playwright-cli list
find "$PWD/.playwright/profiles" -maxdepth 1 -mindepth 1 -type d -exec basename {} \; 2>/dev/null | sort
```

Apply these rules, which override all generic session examples below:

1. **Exactly one workspace profile exists:** use it exclusively. The session name **must equal** the profile directory basename. Reuse its open session if present; otherwise reopen it headed with that profile. Do not create another session or profile.
2. **No workspace profile exists:** create one under `$PWD/.playwright/profiles/<session-name>` by opening a headed browser with `--profile`. Choose a stable, workspace-specific `<session-name>` and use that same name for the session and profile. This is the only case in which a new profile may be created.
3. **More than one workspace profile exists:** do not guess or create another one; ask the user which profile to use.
4. Treat sessions not backed by a profile in the current workspace, including in-memory sessions, as outside/ambiguous. Do not use, alter, or close them unless the user explicitly identifies them.

Examples:

```bash
# One existing profile named "workspace-browser": reuse its same-named session
playwright-cli -s=workspace-browser snapshot

# If it is not open, reopen that exact profile headed
playwright-cli -s=workspace-browser open --headed \
  --profile="$PWD/.playwright/profiles/workspace-browser" https://example.com

# With no profiles, create one stable workspace profile (not an in-memory session)
playwright-cli -s=workspace-browser open --headed \
  --profile="$PWD/.playwright/profiles/workspace-browser" https://example.com
```

Never print saved storage-state, cookies, localStorage, or profile contents; they may contain secrets.

## Quick start

```bash
# With an existing profile, use its basename as the session name.
playwright-cli -s=workspace-browser open --headed \
  --profile="$PWD/.playwright/profiles/workspace-browser" https://example.com
# take a snapshot to inspect the page structure
playwright-cli -s=workspace-browser snapshot
# navigate to another page
playwright-cli -s=workspace-browser goto https://other-page.com
# Close only when the user explicitly identifies this session and asks to close it.
playwright-cli -s=workspace-browser close
```

## Typical browsing workflow

```bash
# 1. Reuse the mandatory profile-backed workspace session.
playwright-cli -s=workspace-browser snapshot

# 2. Interact — click, fill, scroll
playwright-cli -s=workspace-browser click e5        # click element (use ref from snapshot)
playwright-cli -s=workspace-browser fill e3 "text"  # fill input field
playwright-cli -s=workspace-browser press Enter

# 3. Check what's on the page now
playwright-cli -s=workspace-browser --raw eval "() => document.body.innerText.slice(0, 3000)"

# 4. Navigate somewhere else
playwright-cli -s=workspace-browser goto https://another-site.com

# 5. Close only when the user explicitly identifies this session and asks to close it.
playwright-cli -s=workspace-browser close
```

> **Tip**: Use `playwright-cli goto <url>` instead of `curl` for interactive browsing — it handles JS-rendered pages, forms, redirects, and dynamic content.

## Commands

Scope every command with `-s=<profile-name>`, where `<profile-name>` is the selected workspace profile basename. Commands in the reference lists below that omit this flag are shorthand only and must not be run unscoped. Do not run unscoped commands when outside/ambiguous sessions exist.

### Core

```bash
# Open only under the Mandatory workspace profile policy.
playwright-cli -s=<profile-name> open --headed \
  --profile="$PWD/.playwright/profiles/<profile-name>" https://example.com/
playwright-cli -s=<profile-name> goto https://playwright.dev
playwright-cli type "search query"
playwright-cli click e3
playwright-cli dblclick e7
# --submit presses Enter after filling the element
playwright-cli fill e5 "user@example.com"  --submit
playwright-cli drag e2 e8
playwright-cli hover e4
playwright-cli select e9 "option-value"
playwright-cli upload ./document.pdf
playwright-cli check e12
playwright-cli uncheck e12
playwright-cli snapshot
playwright-cli eval "document.title"
playwright-cli eval "el => el.textContent" e5
# get element id, class, or any attribute not visible in the snapshot
playwright-cli eval "el => el.id" e5
playwright-cli eval "el => el.getAttribute('data-testid')" e5
playwright-cli dialog-accept
playwright-cli dialog-accept "confirmation text"
playwright-cli dialog-dismiss
playwright-cli resize 1920 1080
playwright-cli -s=<session-name> close
```

### Navigation

```bash
playwright-cli go-back
playwright-cli go-forward
playwright-cli reload
```

### Keyboard

```bash
playwright-cli press Enter
playwright-cli press ArrowDown
playwright-cli keydown Shift
playwright-cli keyup Shift
```

### Mouse

```bash
playwright-cli mousemove 150 300
playwright-cli mousedown
playwright-cli mousedown right
playwright-cli mouseup
playwright-cli mouseup right
playwright-cli mousewheel 0 100
```

### Save as

```bash
playwright-cli screenshot
playwright-cli screenshot e5
playwright-cli screenshot --filename=page.png
playwright-cli pdf --filename=page.pdf
```

### Tabs

```bash
playwright-cli tab-list
playwright-cli tab-new
playwright-cli tab-new https://example.com/page
playwright-cli tab-close
playwright-cli tab-close 2
playwright-cli tab-select 0
```

### Storage

```bash
playwright-cli state-save
playwright-cli state-save auth.json
playwright-cli state-load auth.json

# Cookies
playwright-cli cookie-list
playwright-cli cookie-list --domain=example.com
playwright-cli cookie-get session_id
playwright-cli cookie-set session_id abc123
playwright-cli cookie-set session_id abc123 --domain=example.com --httpOnly --secure
playwright-cli cookie-delete session_id
playwright-cli cookie-clear

# LocalStorage
playwright-cli localstorage-list
playwright-cli localstorage-get theme
playwright-cli localstorage-set theme dark
playwright-cli localstorage-delete theme
playwright-cli localstorage-clear

# SessionStorage
playwright-cli sessionstorage-list
playwright-cli sessionstorage-get step
playwright-cli sessionstorage-set step 3
playwright-cli sessionstorage-delete step
playwright-cli sessionstorage-clear
```

### Network

```bash
playwright-cli route "**/*.jpg" --status=404
playwright-cli route "https://api.example.com/**" --body='{"mock": true}'
playwright-cli route-list
playwright-cli unroute "**/*.jpg"
playwright-cli unroute
```

### DevTools

```bash
playwright-cli console
playwright-cli console warning
playwright-cli network
playwright-cli run-code "async page => await page.context().grantPermissions(['geolocation'])"
playwright-cli run-code --filename=script.js
playwright-cli tracing-start
playwright-cli tracing-stop
playwright-cli video-start video.webm
playwright-cli video-chapter "Chapter Title" --description="Details" --duration=2000
playwright-cli video-stop
```

## Raw output

The global `--raw` option strips page status, generated code, and snapshot sections from the output, returning only the result value. Use it to pipe command output into other tools. Commands that don't produce output return nothing.

```bash
playwright-cli --raw eval "JSON.stringify(performance.timing)" | jq '.loadEventEnd - .navigationStart'
playwright-cli --raw eval "JSON.stringify([...document.querySelectorAll('a')].map(a => a.href))" > links.json
playwright-cli --raw snapshot > before.yml
playwright-cli click e5
playwright-cli --raw snapshot > after.yml
diff before.yml after.yml
TOKEN=$(playwright-cli --raw cookie-get session_id)
playwright-cli --raw localstorage-get theme
```

## Open parameters
> ⛔ **Reminder:** for any search/scraping/browsing task, open with `--headed`. Headless only after explicit user confirmation. The reference commands below are shorthand: every actual open must include `-s=<profile-name>` and `--profile="$PWD/.playwright/profiles/<profile-name>"` under the Mandatory workspace profile policy.
```bash
# Use specific browser when creating session
playwright-cli open --browser=chrome
playwright-cli open --browser=firefox
playwright-cli open --browser=webkit
playwright-cli open --browser=msedge

# Headed mode (visible browser window — MANDATORY for browsing/scraping unless user explicitly allows headless)
playwright-cli open --headed

# Use persistent profile (by default profile is in-memory)
playwright-cli open --persistent
# Use persistent profile with custom directory
playwright-cli open --profile=/path/to/profile

# Connect to browser via extension
playwright-cli attach --extension

# Start with config file
playwright-cli open --config=my-config.json

> **💡 Remove the `--no-sandbox` infobar**: by default playwright-cli appends `--no-sandbox` to the Chrome command line, which makes Chrome show the warning *"You are using an unsupported command-line flag: --no-sandbox. Stability and security will suffer."* at the top of every page. To remove it, set `chromiumSandbox: true` in the config file — e.g. workspace `.playwright/cli.config.json`:
> ```json
> { "browser": { "launchOptions": { "chromiumSandbox": true } } }
> ```
> (doli-cli repo already ships this config; it is safe because it launches the properly-signed system Chrome, which supports sandboxing on macOS.)

# Close only a profile-backed session the user explicitly identifies and asks to close.
playwright-cli -s=<profile-name> close
# Delete user data only for a session/profile you created or the user explicitly identified
playwright-cli -s=<session-name> delete-data
```

## Snapshots

After each command, playwright-cli provides a snapshot of the current browser state.

```bash
> playwright-cli goto https://example.com
### Page
- Page URL: https://example.com/
- Page Title: Example Domain
### Snapshot
[Snapshot](.playwright-cli/page-2026-02-14T19-22-42-679Z.yml)
```

You can also take a snapshot on demand using `playwright-cli snapshot` command. All the options below can be combined as needed.

```bash
# default - save to a file with timestamp-based name
playwright-cli snapshot

# save to file, use when snapshot is a part of the workflow result
playwright-cli snapshot --filename=after-click.yaml

# snapshot an element instead of the whole page
playwright-cli snapshot "#main"

# limit snapshot depth for efficiency, take a partial snapshot afterwards
playwright-cli snapshot --depth=4
playwright-cli snapshot e34
```

## Targeting elements

By default, use refs from the snapshot to interact with page elements.

```bash
# get snapshot with refs
playwright-cli snapshot

# interact using a ref
playwright-cli click e15
```

You can also use css selectors or Playwright locators.

```bash
# css selector
playwright-cli click "#main > button.submit"

# role locator
playwright-cli click "getByRole('button', { name: 'Submit' })"

# test id
playwright-cli click "getByTestId('submit-button')"
```

## Browser Sessions

Follow the **Mandatory workspace profile policy** above. In particular, use the same stable name for the session and profile directory, and never create an in-memory fallback when a workspace profile exists.

```bash
# Inspect first; a single existing profile is mandatory to reuse.
playwright-cli list
find "$PWD/.playwright/profiles" -maxdepth 1 -mindepth 1 -type d -exec basename {} \; 2>/dev/null | sort

# Reopen the existing profile named "workspace-browser" if its session is closed.
playwright-cli -s=workspace-browser open --headed \
  --profile="$PWD/.playwright/profiles/workspace-browser" https://example.com

# Only when the profiles directory is empty, create this persistent profile/session pair.
playwright-cli -s=workspace-browser open --headed \
  --profile="$PWD/.playwright/profiles/workspace-browser" https://example.com

playwright-cli -s=workspace-browser click e6
playwright-cli -s=workspace-browser close  # only when the user explicitly identifies it and asks to close it
playwright-cli -s=workspace-browser delete-data  # only with explicit user consent
```

Do not use `close-all` or `kill-all`. Never close/kill outside or ambiguous sessions.

## Installation

If global `playwright-cli` command is not available, try a local version via `npx playwright-cli`:

```bash
npx --no-install playwright-cli --version
```

When local version is available, use `npx playwright-cli` in all commands. Otherwise, install `playwright-cli` as a global command:

```bash
npm install -g @playwright/cli@latest
```

## Example: Form submission

```bash
playwright-cli -s=workspace-browser open --headed \
  --profile="$PWD/.playwright/profiles/workspace-browser" https://example.com/form
playwright-cli -s=workspace-browser snapshot

playwright-cli -s=workspace-browser fill e1 "user@example.com"
playwright-cli -s=workspace-browser fill e2 "password123"
playwright-cli -s=workspace-browser click e3
playwright-cli -s=workspace-browser snapshot
# Leave the persistent workspace session open unless the user explicitly asks to close it.
```

## Example: Multi-tab workflow

```bash
playwright-cli -s=workspace-browser open --headed \
  --profile="$PWD/.playwright/profiles/workspace-browser" https://example.com
playwright-cli -s=workspace-browser tab-new https://example.com/other
playwright-cli -s=workspace-browser tab-list
playwright-cli -s=workspace-browser tab-select 0
playwright-cli -s=workspace-browser snapshot
# Leave the persistent workspace session open unless the user explicitly asks to close it.
```

## Example: Debugging with DevTools

```bash
playwright-cli -s=workspace-browser open --headed \
  --profile="$PWD/.playwright/profiles/workspace-browser" https://example.com
playwright-cli -s=workspace-browser click e4
playwright-cli -s=workspace-browser fill e7 "test"
playwright-cli -s=workspace-browser console
playwright-cli -s=workspace-browser network
# Leave the persistent workspace session open unless the user explicitly asks to close it.
```

```bash
playwright-cli -s=workspace-browser tracing-start
playwright-cli -s=workspace-browser click e4
playwright-cli -s=workspace-browser fill e7 "test"
playwright-cli -s=workspace-browser tracing-stop
# Leave the persistent workspace session open unless the user explicitly asks to close it.
```

## Specific tasks

* **Running and Debugging Playwright tests** [references/playwright-tests.md](references/playwright-tests.md)
* **Request mocking** [references/request-mocking.md](references/request-mocking.md)
* **Running Playwright code** [references/running-code.md](references/running-code.md)
* **Browser session management** [references/session-management.md](references/session-management.md)
* **Storage state (cookies, localStorage)** [references/storage-state.md](references/storage-state.md)
* **Test generation** [references/test-generation.md](references/test-generation.md)
* **Tracing** [references/tracing.md](references/tracing.md)
* **Video recording** [references/video-recording.md](references/video-recording.md)
* **Inspecting element attributes** [references/element-attributes.md](references/element-attributes.md)
