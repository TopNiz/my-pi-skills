---
name: openwebui-remote
description: Remotely inspect and administer Open WebUI through the public owui Python CLI. Use for system configuration, user accounts, default permissions, current-user settings, API authentication checks, and headless Open WebUI administration. Enforces read-before-write, dry runs, explicit confirmation, least privilege, and strict credential hygiene.
allowed-tools: Bash(owui:*)
---

# Open WebUI Remote Control

Use the `owui` CLI as the supported administration layer. Prefer its stable commands over hand-written HTTP calls or generated operation names.

## Safety rules

1. Never print, log, request in chat, or pass an API key, JWT, password, cookie, or secret as a command argument.
2. Use a named profile backed by the operating-system keyring. `OPENWEBUI_API_KEY` is allowed only when injected securely into the process environment.
3. Treat reads as the default. Before every mutation, inspect current state and run the corresponding `--dry-run` command when available.
4. Show the user the non-secret proposed changes and obtain explicit confirmation immediately before applying them with `--yes`.
5. After a mutation, read the affected resource again and verify the expected result.
6. Never use a shared administrator key in browser or mobile code. Use one least-privilege service account per application.
7. Do not invoke undocumented destructive generated-client operations without a reviewed plan and explicit user consent.
8. Minimize personal data in chat output. Summarize user-list results instead of reproducing unnecessary names or email addresses.

## Installation

The CLI is distributed from its GitHub repository. Install the released version with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install 'git+https://github.com/TopNiz/openwebui-cli.git@v0.1.0a2'
```

Verify the installation:

```bash
command -v owui >/dev/null && owui --version
owui profile list
```

Installing or upgrading a tool changes the local environment. Do not perform it automatically: show the command and obtain the user's explicit approval first.

## Select and verify a profile

```bash
owui --profile <profile> auth status
```

This displays account identity but never the key. If no profile exists, create only non-secret metadata and let the user store the key through hidden input:

```bash
owui profile set <profile> \
  --url https://openwebui.example.org \
  --keyring-service <service> \
  --keyring-username <account> \
  --activate
owui auth keyring-store --for-profile <profile>
```

Never invent keyring identifiers when an existing organizational convention may apply; ask first.

## Read system settings

```bash
owui --profile <profile> system config get
owui --profile <profile> system config get ENABLE_API_KEYS
```

For a change, always dry-run first:

```bash
owui --profile <profile> system config set ENABLE_SIGNUP false --dry-run
```

After explicit confirmation:

```bash
owui --profile <profile> system config set ENABLE_SIGNUP false --yes
owui --profile <profile> system config get ENABLE_SIGNUP
```

## Manage users

Read operations:

```bash
owui --profile <profile> users list
owui --profile <profile> users get <user-id-or-email>
```

Account creation and password reset use hidden input by default. Ask the user to complete that protected prompt. For non-interactive automation, `--password-stdin` may receive input directly from an approved secret manager; never use `echo`, a literal value, or a temporary plaintext file.

Privilege changes and password resets require explicit confirmation. The CLI discards session tokens returned by account creation.

## Manage default permissions

```bash
owui --profile <profile> permissions get
owui --profile <profile> permissions set features.api_keys false --dry-run
```

Open WebUI permissions are additive. Review the whole permission document and relevant groups before granting access. Apply only after confirmation, then verify:

```bash
owui --profile <profile> permissions set features.api_keys false --yes
owui --profile <profile> permissions get
```

## Manage current-user settings

These settings belong only to the account owning the selected API key:

```bash
owui --profile <profile> user-settings get
owui --profile <profile> user-settings set ui.language nl --dry-run
```

Apply only after confirmation and verify the affected path.

## Delete a Knowledge base (controlled API exception)

The stable `owui` CLI does not currently manage Knowledge bases. Deleting one is destructive, so use this narrowly scoped, documented API workflow only after the user explicitly identifies the exact Knowledge base and confirms its deletion.

1. Read the target first and verify both its immutable ID and expected name. Do not select a resource by name alone.
2. Confirm the public API route and method in the instance OpenAPI specification: `DELETE /api/v1/knowledge/{id}/delete`.
3. Read the profile metadata, retrieve its key from the OS keyring into a shell variable, and use the **profile public HTTPS URL**. Never print the key or substitute another HTTP method if the request fails.
4. Delete the exact ID, then verify that `GET /api/v1/knowledge/{id}` returns `404`.

```bash
PROFILE=<profile-name>
KNOWLEDGE_ID=<confirmed-knowledge-id>
EXPECTED_NAME='<confirmed knowledge-base name>'

PROFILE_JSON=$(owui profile show "$PROFILE")
BASE_URL=$(printf '%s' "$PROFILE_JSON" | jq -r '.base_url')
KEYRING_SERVICE=$(printf '%s' "$PROFILE_JSON" | jq -r '.keyring_service')
KEYRING_USERNAME=$(printf '%s' "$PROFILE_JSON" | jq -r '.keyring_username')
export OPENWEBUI_API_KEY="$(security find-generic-password \
  -s "$KEYRING_SERVICE" -a "$KEYRING_USERNAME" -w)"
trap 'unset OPENWEBUI_API_KEY' EXIT

# Pre-flight: refuse to delete a different resource.
name=$(curl --fail --silent --show-error \
  --header "Authorization: Bearer ${OPENWEBUI_API_KEY}" \
  "$BASE_URL/api/v1/knowledge/$KNOWLEDGE_ID" \
  | jq -r '.name')
[ "$name" = "$EXPECTED_NAME" ]

# Apply only after explicit user confirmation.
curl --fail --silent --show-error --request DELETE \
  --header "Authorization: Bearer ${OPENWEBUI_API_KEY}" \
  "$BASE_URL/api/v1/knowledge/$KNOWLEDGE_ID/delete" >/dev/null

# Verification: the exact resource must be absent.
status=$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --header "Authorization: Bearer ${OPENWEBUI_API_KEY}" \
  "$BASE_URL/api/v1/knowledge/$KNOWLEDGE_ID")
[ "$status" = 404 ]
```

A deleted Knowledge base can leave its previously uploaded files in Open WebUI storage. Do not delete those files unless the user explicitly asks for that separate destructive operation.

## Discover commands

Use embedded help instead of guessing flags or payloads:

```bash
owui --help
owui <group> --help
owui <group> <command> --help
```

See `references/COMMANDS.md` for the supported command map and escalation guidance.
