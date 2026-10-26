---
name: trash-files
description: Move files and folders to the system Trash or Recycle Bin instead of permanently deleting them. Use whenever a user asks to delete, remove, clean up, or discard filesystem items; permanently delete only when the user explicitly requests permanent deletion of the identified target.
---

# Safe file removal

When asked to delete, remove, clean up, or discard files, treat that as a request to move them to the system Trash or Recycle Bin, not to permanently erase them.

## Safety rules

- Work only on targets the user identified and within the current workspace, unless the user explicitly specifies another location.
- Inspect and resolve the exact target paths before acting. If a path, wildcard, directory scope, or intended set is ambiguous, ask before proceeding.
- Do not broaden a request to include related files, hidden files, generated files, or parent directories.
- Prefer the platform's Trash or Recycle Bin mechanism. Never substitute permanent deletion when a trash mechanism is unavailable; explain the limitation and ask how to proceed.
- Report which identified items were successfully moved to Trash and any failures. Do not claim success if the operation failed or could not be verified.

## Move items to Trash

Use an installed trash utility when available, such as `trash` on macOS, `gio trash` on Linux desktops, or an established platform-specific Recycle Bin command on Windows. Pass each resolved path as a separate argument, preserving spaces and special characters. Avoid shell glob expansion; resolve and verify matches first.

On macOS, if no trash utility is available, Finder's `delete` action can move a path to the Trash. Use a safely quoted/escaped path and verify the result. If no reliable platform trash mechanism is available, stop and ask rather than using `rm`, `rmdir`, or another permanent-delete operation as a fallback.

## Permanently delete

Permanent deletion is allowed only when the user explicitly asks for permanent deletion, such as "permanently delete" or "delete without moving to Trash," and the exact target is clear. A general request to "delete" or "remove" is not sufficient.

- If the target is unclear, broad, or includes a wildcard, ask the user to confirm the exact target set before permanent deletion.
- Before using an irreversible command, state the exact target paths and ask for confirmation if the request did not already clearly identify them and explicitly authorize permanent deletion.
- Once authorized, permanently delete only those exact targets. Do not use broad recursive commands against directories unless the user explicitly identified those directories and requested their permanent deletion.
- Never use permanent deletion to work around permission errors, locked files, cross-volume behavior, or Trash failures. Stop and explain the issue.
