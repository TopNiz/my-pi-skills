---
name: web-browser
description: Navigate the web, browse pages, search, extract content, and fill forms using a headless browser (Playwright). Also supports web testing and debugging.
allowed-tools: Bash(playwright-cli:*) Bash(npx:*) Bash(npm:*)
---

# Web Browser (playwright-cli)

**Primary use: browsing & navigating the web.** Web testing is a secondary capability.

## Workspace-local persistent sessions

Before starting a new browser, always check whether the current workspace already has a local persistent Playwright session/profile to reuse. **Only touch sessions that clearly belong to the current workspace or that this agent/session created.** Do not attach to, modify, or close outside/ambiguous sessions.

### List local sessions and separate them from outside sessions

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

### Reuse or open only workspace sessions

```bash
# if a named workspace-owned session is already open, use it
playwright-cli -s=<session-name> snapshot

# if no session is open but a workspace profile exists, reopen it headed
# common convention: .playwright/profiles/<session-name>
playwright-cli -s=<session-name> open --headed --profile="$PWD/.playwright/profiles/<session-name>" https://example.com

# if no workspace profile/session exists and a temporary session is needed,
# create a clearly named task/workspace session instead of default when possible
playwright-cli -s=web-browser open --headed https://example.com
```

Rules:
- Prefer an existing workspace-owned session over creating a new session.
- Prefer workspace profiles under `.playwright/profiles/` for sites where the user is already authenticated.
- Treat open sessions whose names do not match current-workspace profiles as outside/ambiguous; do not use or close them unless the user explicitly identifies them.
- Prefer named sessions (`-s=<name>`) over `default`. If the CLI forces `default`, touch it only if this agent/session created it.
- Use `--headed` when reopening persistent sessions so the user can interact with login/captcha/2FA if needed.
- Never print saved storage-state, cookies, localStorage, or profile contents; they may contain secrets.
- Only create a new browser/session when no suitable local session/profile exists.

## Quick start

```bash
# open a named browser session and go to a page (headless by default)
playwright-cli -s=web-browser open https://example.com
# take a snapshot to inspect the page structure
playwright-cli -s=web-browser snapshot
# navigate to another page
playwright-cli -s=web-browser goto https://other-page.com
# close only the session you created when done
playwright-cli -s=web-browser close
```

## Typical browsing workflow

```bash
# 1. Open and navigate using a named session owned by this task/workspace
playwright-cli -s=web-browser open https://example.com

# 2. Snapshot shows the page with element refs (e1, e2, …)
playwright-cli -s=web-browser snapshot

# 3. Interact — click, fill, scroll
playwright-cli -s=web-browser click e5        # click element (use ref from snapshot)
playwright-cli -s=web-browser fill e3 "text"  # fill input field
playwright-cli -s=web-browser press Enter

# 4. Check what's on the page now
playwright-cli -s=web-browser --raw eval "() => document.body.innerText.slice(0, 3000)"

# 5. Navigate somewhere else
playwright-cli -s=web-browser goto https://another-site.com

# 6. Close only this disposable session
playwright-cli -s=web-browser close
```

> **Tip**: Use `playwright-cli goto <url>` instead of `curl` for interactive browsing — it handles JS-rendered pages, forms, redirects, and dynamic content.

## Commands

Unless the user explicitly identified a different workspace-owned session, scope commands with `-s=<session-name>` for the session you created or selected. Do not run unscoped commands when outside/ambiguous sessions exist.

### Core

```bash
playwright-cli -s=<session-name> open
# open and navigate right away
playwright-cli -s=<session-name> open https://example.com/
playwright-cli -s=<session-name> goto https://playwright.dev
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
```bash
# Use specific browser when creating session
playwright-cli open --browser=chrome
playwright-cli open --browser=firefox
playwright-cli open --browser=webkit
playwright-cli open --browser=msedge

# Headed mode (visible browser window — required for visual debugging)
playwright-cli open --headed

# Use persistent profile (by default profile is in-memory)
playwright-cli open --persistent
# Use persistent profile with custom directory
playwright-cli open --profile=/path/to/profile

# Connect to browser via extension
playwright-cli attach --extension

# Start with config file
playwright-cli open --config=my-config.json

# Close only the browser session you created or the user explicitly identified
playwright-cli -s=<session-name> close
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

```bash
# first separate current-workspace sessions/profiles from outside/ambiguous sessions
playwright-cli list
find "$PWD/.playwright/profiles" -maxdepth 1 -mindepth 1 -type d -exec basename {} \; 2>/dev/null | sort

OPEN_SESSIONS=$(playwright-cli list 2>/dev/null | awk '/^- /{gsub(":$","",$2); print $2}' | sort)
LOCAL_PROFILES=$(find "$PWD/.playwright/profiles" -maxdepth 1 -mindepth 1 -type d -exec basename {} \; 2>/dev/null | sort)
printf '%s\n' "Workspace-owned open sessions:"
comm -12 <(printf '%s\n' "$OPEN_SESSIONS") <(printf '%s\n' "$LOCAL_PROFILES")
printf '%s\n' "Outside or ambiguous open sessions (do not touch):"
comm -23 <(printf '%s\n' "$OPEN_SESSIONS") <(printf '%s\n' "$LOCAL_PROFILES")

# reuse an existing workspace profile as a named, headed session
playwright-cli -s=mysession open --headed --profile="$PWD/.playwright/profiles/mysession" https://example.com

# create a new named browser session only when no suitable workspace session/profile exists
playwright-cli -s=mysession open example.com --persistent
# same with a manually specified profile directory, only when requested explicitly
playwright-cli -s=mysession open example.com --profile="$PWD/.playwright/profiles/mysession"
playwright-cli -s=mysession click e6
playwright-cli -s=mysession close  # stop only this named browser if you created it or the user identified it
playwright-cli -s=mysession delete-data  # only for a profile/session you created or the user identified

playwright-cli list
# Do NOT use close-all or kill-all unless the user explicitly requests it and confirms every affected session belongs to this task/workspace.
# Never close/kill outside or ambiguous sessions.
```

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
playwright-cli -s=web-browser open https://example.com/form
playwright-cli -s=web-browser snapshot

playwright-cli -s=web-browser fill e1 "user@example.com"
playwright-cli -s=web-browser fill e2 "password123"
playwright-cli -s=web-browser click e3
playwright-cli -s=web-browser snapshot
playwright-cli -s=web-browser close
```

## Example: Multi-tab workflow

```bash
playwright-cli -s=web-browser open https://example.com
playwright-cli -s=web-browser tab-new https://example.com/other
playwright-cli -s=web-browser tab-list
playwright-cli -s=web-browser tab-select 0
playwright-cli -s=web-browser snapshot
playwright-cli -s=web-browser close
```

## Example: Debugging with DevTools

```bash
playwright-cli -s=web-browser open https://example.com
playwright-cli -s=web-browser click e4
playwright-cli -s=web-browser fill e7 "test"
playwright-cli -s=web-browser console
playwright-cli -s=web-browser network
playwright-cli -s=web-browser close
```

```bash
playwright-cli -s=web-browser open https://example.com
playwright-cli -s=web-browser tracing-start
playwright-cli -s=web-browser click e4
playwright-cli -s=web-browser fill e7 "test"
playwright-cli -s=web-browser tracing-stop
playwright-cli -s=web-browser close
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
