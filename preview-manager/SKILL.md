---
name: preview-manager
description: Manage Preview app documents — list open PDFs, open new ones, and close specific documents by name without affecting other open files. **macOS only.** (Uses AppleScript to control Preview.app.)
compatibility: opencode
---

# Preview Manager

Manage PDF previews using macOS Preview app via AppleScript. Use this skill whenever you need to open a PDF for visual inspection or close it after processing, without interfering with other documents the user has open.

---

## Preflight: confirm GUI session access

Before using AppleScript against Preview, verify that the command is running in the logged-in GUI user's workspace. This is especially important over SSH, where GUI AppleEvents often time out or are blocked by macOS privacy/session isolation.

Run this preflight check first:

```bash
console_user=$(stat -f %Su /dev/console 2>/dev/null || echo "unknown")
current_user=$(id -un)

if [ -n "${SSH_CONNECTION:-}${SSH_TTY:-}" ]; then
  echo "NOT_GUI_SESSION: running over SSH"
elif [ "$console_user" != "$current_user" ]; then
  echo "NOT_GUI_SESSION: current user '$current_user' is not console GUI user '$console_user'"
elif ! /usr/bin/osascript -e 'tell application "Finder" to name of desktop' >/dev/null 2>&1; then
  echo "GUI_SESSION_UNAVAILABLE: AppleScript cannot access the GUI session"
else
  echo "GUI_SESSION_OK: AppleScript can access the logged-in GUI workspace"
fi
```

If the result is not `GUI_SESSION_OK`, do **not** attempt to open, list, or close Preview documents automatically. Explain the limitation and ask the user to either:

- run the action from a local terminal in the logged-in macOS desktop session,
- grant/confirm macOS Automation permissions if prompted locally, or
- manually perform the Preview action and confirm when done.

## List open documents

Always list open Preview documents before closing one, so you can show the user what's open and close only the correct file. Only run this after the preflight returns `GUI_SESSION_OK`.

```applescript
tell application "Preview"
    set docNames to name of every document
end tell
```

## Open a PDF

```bash
open -a Preview "/path/to/document.pdf"
```

## Close a specific document by name

Close by exact document filename — **never** use `close first window` or `close window 1`, as it may close a document the user wants to keep open.

```bash
osascript -e 'tell application "Preview" to close (every document whose name is "filename.pdf")'
```

## Workflow

1. **Run the GUI session preflight** above.
2. If the preflight is not `GUI_SESSION_OK`, stop and ask the user how they want to proceed manually or from a local GUI terminal.
3. **Open** the PDF using `open -a Preview`.
4. **Wait** for user to inspect it and give confirmation.
5. **List** open documents to see what else is open.
6. **Show the list** to the user and confirm which one to close.
7. **Close** by exact name using the close-by-name AppleScript.

## Example

```bash
# List open documents
osascript -e 'tell application "Preview" to set docNames to name of every document'

# Open a PDF
open -a Preview "/path/to/invoice.pdf"

# Close a specific PDF by name
osascript -e 'tell application "Preview" to close (every document whose name is "invoice.pdf")'
```

## Notes

- Always list before closing — the user may have unrelated documents open.
- Close by document name, not by window index.
- If multiple documents have the same name (unlikely), close by name still works on all matching.
