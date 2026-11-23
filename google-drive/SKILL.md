---
name: google-drive
description: Access configured Google Drive accounts for any user. List and inspect files, download or export documents, create folders, upload files, replace ordinary file contents, rename or move items, and move explicitly confirmed items to Trash or restore them. Uses a skill-local OAuth client and separate authorization files for each configured account. Permanent deletion and emptying Trash are blocked.
compatibility: Python 3.10 or newer with the dependencies in pyproject.toml
---

# Google Drive

## Configuration and portability

This skill is not tied to a company, user, operating system, or credential store. Each installation supplies its own local configuration and credentials. Never use an account merely because it appears in an example.

1. Copy `config.json` to `config.local.json` only when the local configuration does not already exist.
2. Set `default_account` to a configured primary Google account address.
3. Add each permitted primary account address under `accounts`. Account addresses are case-insensitive; use lowercase configuration keys.
4. Store this skill's desktop Google OAuth client JSON at `accounts.drive/credentials.drive.json` and set `oauth_client_file` accordingly. The same Google OAuth app may serve Gmail and Drive, but keep a separate client JSON copy inside this skill folder. Never share another skill's account authorization files. An account entry can select a different client file stored inside this skill folder.
5. Keep `credentials_dir` set to `./accounts.drive`. Relative paths resolve against this skill directory. Each installation supplies and protects its own local files.
6. Install the dependencies with `uv sync` in this skill directory only with explicit user permission. Alternatively, set `python_runtime` in the local configuration to an existing virtual environment's Python executable with the required dependencies. The script does not install packages automatically.
7. Enable Google Drive API in the selected OAuth app's project. Ensure the selected account is allowed by the app's consent configuration.

Example local configuration:

```json
{
  "default_account": "person@example.com",
  "credentials_dir": "./accounts.drive",
  "oauth_client_file": "./accounts.drive/credentials.drive.json",
  "accounts": {
    "person@example.com": {},
    "person@another-company.example": {
      "oauth_client_file": "./accounts.drive/second-client.json"
    }
  }
}
```

The example accounts are placeholders. Other people must supply their own account addresses and OAuth clients. Do not copy another user's client secrets or account credentials.

`config.local.json`, `accounts.drive/`, the local virtual environment, and credential filename patterns are excluded by this skill's `.gitignore`. Git ignores do not prevent Nextcloud, Google Drive, backup, or other synchronization. Warn the user before authorization if this skill folder is synchronized or shared. Do not silently relocate credentials outside the skill folder. Never commit or print credentials. On POSIX systems, newly created credential directories use mode `0700` and files use `0600`. On Windows, the user must also protect the location with account-specific filesystem permissions.

## Skill-local credential layout

Use the same storage strategy as the Gmail skill. A copy of the same OAuth client configuration is allowed, but this Drive skill keeps its own client file and separate Drive authorizations:

```text
accounts.drive/
  credentials.drive.json
  person@example.com/
    token.drive.json
  person@another-company.example/
    token.drive.json
```

Each Drive account receives its own separate authorization in `accounts.drive/<primary-address>/token.drive.json`. Existing Gmail and Calendar authorizations are not changed or overwritten. The requested permission is `https://www.googleapis.com/auth/drive`; this includes capabilities beyond the operations exposed by this skill. Permanent deletion is blocked by the skill, not by Google's scope.

## Authorization and account selection

Run `scripts/drive.py` with Python 3. Resolve the script path against this skill directory. Put `--account` before the command:

```bash
python3 scripts/drive.py --account person@example.com authorize
python3 scripts/drive.py --account person@example.com status
```

Omit `--account` to use the configured default. An unknown account fails instead of falling back to another account.

Authorization opens the system browser and waits up to five minutes for approval. It never prints the authorization URL, callback URL, codes, or credentials. Select the requested account and approve the Drive permission. The Drive API verifies the primary account before saving authorization and before each operation. An account mismatch stops the operation. A stored authorization is never silently replaced; replacement requires a separate, approved credential-management workflow.

The access credential refreshes in memory when needed. The initial refresh credential remains in its account's private local file. No credentials are printed during status checks. Suppress raw OAuth exceptions, HTTP error bodies, callback requests, and debug logging.

## Read operations

The following examples use the configured default account. Add `--account <configured-primary-address>` before any command to select another account.

```bash
python3 scripts/drive.py list
python3 scripts/drive.py list --parent FOLDER_ID --limit 50
python3 scripts/drive.py list --parent FOLDER_ID --limit 1000
python3 scripts/drive.py list --trash
python3 scripts/drive.py info FILE_ID
python3 scripts/drive.py download FILE_ID --out /explicitly/approved/path
python3 scripts/drive.py export FILE_ID --mime application/pdf --out /explicitly/approved/path.pdf
```

Lists fetch pages internally, with a limit of 50 items by default and at most 1,000 per call. `has_more: true` means the output is incomplete. Do not describe such output as a complete folder listing. Pagination cursors remain in memory and are not printed. Ask before adding a larger or persistent listing workflow.

Downloads and exports require an explicit user request for the destination. They refuse to overwrite existing paths or create missing parent folders. A failed transfer can leave a partial newly created file; do not delete that file without user consent. Do not download files merely to check access. Follow workspace restrictions unless the user explicitly approves another location.

## Create and edit

All remote write commands default to a dry run. A dry run may read metadata, but does not modify Drive. Inspect the preview and obtain explicit user approval for the exact account, operation, and targets before executing it. A request to connect Drive is not permission to create or edit Drive files.

```bash
# Dry-run examples:
python3 scripts/drive.py mkdir "Folder name" --parent FOLDER_ID
python3 scripts/drive.py upload /approved/local/file.pdf --parent FOLDER_ID
python3 scripts/drive.py update FILE_ID /approved/local/replacement.pdf
python3 scripts/drive.py rename FILE_ID "New name"
python3 scripts/drive.py move FILE_ID --parent DESTINATION_FOLDER_ID

# After explicit user approval, add both flags:
# --execute --confirm-account <selected-primary-address>
# Existing-item operations also require: --confirm-id FILE_ID
```

Uploads and content replacements are limited to 50 MiB. A confirmed replacement overwrites the target's current contents. Never infer approval for a replacement from approval to upload a different file. Uploads create new files and do not replace matching names automatically. Folder creation can create a duplicate name; ask if the intended target is ambiguous. Inspect folder identity and ownership where needed.

The script supports ordinary file-content updates and Drive metadata changes. It does not edit the contents of native Google Docs, Sheets, or Slides. Those require their respective APIs or a separate, explicitly approved workflow. Native documents can be exported with the export command.

## Removal policy: Trash only

1. Treat requests to remove or delete as requests to move to Google Drive Trash.
2. Inspect the exact item ID, name, type, parents, current Trash state, and capabilities. Never select removal targets by broad patterns.
3. Explain folder effects: moving a folder to Trash also affects its contents.
4. Show the dry run and obtain explicit confirmation for the exact account and item before executing it.
5. Use only a metadata update with `trashed: true`. Verify the returned state.
6. If Trash fails, stop. Never fall back to permanent deletion or remove access permissions instead.
7. Restore only explicitly identified and approved items with `trashed: false`.

```bash
python3 scripts/drive.py trash FILE_ID
python3 scripts/drive.py trash FILE_ID --execute --confirm-account person@example.com --confirm-id FILE_ID
python3 scripts/drive.py restore FILE_ID
python3 scripts/drive.py restore FILE_ID --execute --confirm-account person@example.com --confirm-id FILE_ID
```

There is no permanent-delete command or empty-Trash command. The HTTP adapter rejects all DELETE requests. Do not bypass this adapter with another client. Google normally permanently deletes items after 30 days in Trash; moving to Trash is not indefinite retention. Shared-drive permissions and retention rules can differ.

## Scope discipline

Only touch items the user explicitly identified or that this agent created. Confirm ambiguous folder IDs, shared-drive boundaries, and effects on other users before writes. Do not create test folders or upload test files to verify access. Verify a connection with `status`, which reads only account metadata. This skill handles Drive, not Gmail operations. Never send email as part of this skill.
