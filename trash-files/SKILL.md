---
name: trash-files
description: Move files and folders into private, gitignored storage inside this skill, list stored items, and restore them remotely without a desktop. Use for filesystem deletion, cleanup, trash inspection, and recovery. Permanently delete only when the user explicitly requests it for identified targets.
compatibility: Python 3 on macOS or Linux with an exclusive rename API; source and storage must be on the same filesystem.
---

# Private trash and remote recovery

Use this skill's own `.trash/` directory, not the system Trash or Recycle Bin.
Resolve all script paths relative to this skill directory. The examples below use
its current installation path.

## Safety rules

- Only manage targets the user identified. Stay within the current workspace unless the user authorizes another location.
- Moving a file into this trash requires user consent, just like other file changes. A request to delete or remove an identified file authorizes moving it here, not permanent deletion.
- Inspect exact paths before moving them. Do not broaden the request to related files, parent directories, hidden files, or wildcard matches.
- Never move an item that is in active use without explaining the risk and obtaining specific approval.
- Never use the system Trash as a fallback. Do not fall back to permanent deletion or copy/delete operations when a move fails.
- Report each successful move and its restore ID. Batch operations can partly succeed if a later move fails. Check records after any interrupted or failed operation.
- Do not print file contents, credentials, or secrets when inspecting stored items.
- Do not move anything into this storage unless the repository ignores it. Verify the ignore rule first.
- Never commit, push, or upload `.trash/`, payloads, or restore records. The directory is private storage, not encrypted storage.

## Storage layout

```text
trash-files/
  scripts/trash.py
  tests/test_trash.py
  .trash/                       # Private, mode 0700, gitignored
    .lock
    YYYYMMDD-<random-id>/
      record.json               # Original absolute path and operation state
      payload                   # Original file, directory, or symlink
```

The script generates date prefixes from the machine's current local date.
Each item receives a unique ID. Restored entries retain their records but no payload.
The skills repository must contain this root `.gitignore` rule:

```gitignore
/trash-files/.trash/
```

Verify it without reading stored contents:

```bash
git -C /Users/nizarayed/.agents/skills check-ignore trash-files/.trash/probe
```

Moves preserve files, directories, and symlinks on the same filesystem.
Cross-filesystem moves are refused. The script does not request elevated access,
change source permissions, bypass macOS privacy controls, or require a desktop.

## Move approved items into trash

Pass each verified absolute path as a separate argument. Do not use shell globs.
Use `--` before paths so filenames cannot become options.

```bash
python3 /Users/nizarayed/.agents/skills/trash-files/scripts/trash.py put -- /absolute/path/to/item
```

The script writes a restore record before moving the item, then prints a JSON record
with its ID and original path. Keep the ID in the user-facing completion report.
The script serializes operations and uses exclusive moves to prevent overwriting.

## List stored items

```bash
python3 /Users/nizarayed/.agents/skills/trash-files/scripts/trash.py list
```

Each JSON line contains the ID, original path, date, state, and indicators showing
whether the stored payload and original path currently exist.
To include records for completed restores:

```bash
python3 /Users/nizarayed/.agents/skills/trash-files/scripts/trash.py list --all
```

Listing creates the private storage and its lock file on first use.
This storage does not include files previously moved to the system Trash.

## Restore remotely

1. List stored items and identify the exact restore ID.
2. Obtain approval for the item and destination. A clear user request to restore that item is sufficient.
3. Restore to the original path:

```bash
python3 /Users/nizarayed/.agents/skills/trash-files/scripts/trash.py restore <ID>
```

If the original path is occupied or another location is requested, obtain approval
for an exact alternative path and use:

```bash
python3 /Users/nizarayed/.agents/skills/trash-files/scripts/trash.py restore <ID> --to /absolute/path/to/recovered-item
```

`--to` is the full destination name, not just a parent folder. The parent must
already exist. Restore never replaces an existing file, directory, or symlink.
The destination must be on the same filesystem as storage.

A `prepared` or `restoring` record can remain after an interruption. If the payload
is present, restore can recover it. If no payload is present, inspect the recorded
original and restore paths without changing them. Ask the user before taking any
recovery action whose correct target is uncertain. Do not edit records to force a move.

## Disk space and permanent deletion

Moving files here does not free disk space. There is no automatic expiry or purge.
Do not modify or empty `.trash/` just because the user asks for general cleanup.
Permanent deletion requires an explicit request identifying the exact stored items.
Before performing it, identify their payload paths and explain that recovery through
this skill will no longer be possible. If the target or authorization is unclear, ask.
The script intentionally has no purge command.

## Tests

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s /Users/nizarayed/.agents/skills/trash-files/tests -v
```

Tests create and remove only their own temporary fixtures inside `.trash/`.
They do not move user files or access the system Trash.
