---
name: preview-manager
description: Manage Preview app documents — list open PDFs, open new ones, and close specific documents by name without affecting other open files. **macOS only.** (Uses AppleScript to control Preview.app.)
compatibility: opencode
---

# Preview Manager

Manage PDF previews using macOS Preview app via AppleScript. Use this skill whenever you need to open a PDF for visual inspection or close it after processing, without interfering with other documents the user has open.

---

## List open documents

Always list open Preview documents before closing one, so you can show the user what's open and close only the correct file.

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

1. **Open** the PDF using `open -a Preview`
2. **Wait** for user to inspect it and give confirmation
3. **List** open documents to see what else is open
4. **Show the list** to the user and confirm which one to close
5. **Close** by exact name using the close-by-name AppleScript

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
