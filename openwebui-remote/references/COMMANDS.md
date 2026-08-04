# Supported command map

## Non-mutating

- `owui profile list`
- `owui profile show [NAME]`
- `owui auth status`
- `owui system config get [KEY]`
- `owui users list`
- `owui users get ID_OR_EMAIL`
- `owui permissions get`
- `owui user-settings get`

Export commands write local files and therefore require an explicit destination and normal file-change consent. They refuse to overwrite unless `--force` is supplied.

## Mutating with dry run

- `owui system config set ... --dry-run`
- `owui system config apply ... --dry-run`
- `owui permissions set ... --dry-run`
- `owui permissions apply ... --dry-run`
- `owui user-settings set ... --dry-run`
- `owui user-settings apply ... --dry-run`

After user confirmation, replace `--dry-run` with `--yes`.

## Mutating without dry run

- `owui profile set`
- `owui profile use`
- `owui auth keyring-store`
- `owui users create`
- `owui users update`
- `owui users reset-password`

Inspect relevant state first, explain the exact impact, and obtain explicit confirmation. Password operations must use hidden input or protected stdin from a secret manager.

## Controlled API exception: delete a Knowledge base

The stable `owui` CLI has no Knowledge-base commands. The documented workflow in `../SKILL.md` permits only deletion of a user-confirmed, exact Knowledge-base ID through the official OpenAPI route `DELETE /api/v1/knowledge/{id}/delete`.

It requires: read-and-name verification before deletion, explicit confirmation immediately before the request, an OS-keyring-backed profile, use of the profile public HTTPS URL, and a `404` read-after-delete verification. Do not infer deletion of standalone uploaded files: they require separate explicit consent.

## Escalate to project development

Open a feature issue when a required workflow is absent from the stable CLI. Include:

- business need and users;
- exact Open WebUI version;
- relevant endpoint, if known;
- expected input/output;
- authorization and data sensitivity;
- mutation and rollback behavior;
- acceptance tests.

Do not bypass a missing high-level command with an arbitrary destructive endpoint merely because it exists in the generated client.
