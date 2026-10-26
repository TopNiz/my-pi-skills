---
name: rocket-admin
description: Manage the Rocket.Chat workspace at rocket.codimeo.com through its live REST API. Covers users, channels, groups, teams, rooms, roles, permissions, settings, messages, integrations, statistics, and moderation. Uses a dedicated admin bot token, blocks hard deletes by default, and reads the live OpenAPI spec at /api/docs/json for per-endpoint details.
allowed-tools: Bash(bash:*) Bash(curl:*) Bash(jq:*) Bash(python3:*) Bash(ssh:*)
---

# Rocket.Chat Admin (REST API)

Manage a Rocket.Chat workspace through its REST API. The skill is built around a live OpenAPI spec, so endpoint details never go stale.

## Server facts

| Item | Value |
|---|---|
| Public URL | `https://rocket.codimeo.com` |
| Version | Rocket.Chat 8.9 |
| Live OpenAPI | `https://rocket.codimeo.com/api/docs/json` (OpenAPI 3.0.3, no auth) |
| Full spec | add `?withUndocumented=true` (648 paths, 693 operations) |
| Swagger UI | `https://rocket.codimeo.com/api-docs` |
| Auth headers | `X-User-Id` and `X-Auth-Token` |
| Docker host | `mac-ubuntu-server-2` (192.168.0.6), compose dir `~/rocketchat` |

The skill uses the public HTTPS URL so it works outside the LAN. The internal bind is `192.168.0.6:3000`, not `localhost:3000`.

## Setup (one time)

The skill authenticates as a dedicated admin bot, not as your personal account.

1. Create an admin personal access token in Rocket.Chat. Click your account
   profile icon, then **Profile > Personal Access Tokens** (direct URL:
   `https://rocket.codimeo.com/account/tokens`). Enter a token name, choose
   **Ignore Two Factor Authentication**, click **Add**, verify with your
   password or 2FA code if prompted, then copy the **user ID** and **access
   token** from the success dialog. The token is shown only once.
2. Give it to the setup script through the environment or a file:

```bash
export RC_ADMIN_USER_ID='...'
export RC_ADMIN_TOKEN='...'
bash scripts/setup-bot.sh
```

Or write the two values to `~/.rocket-admin-setup.env` and run `setup-bot.sh`.

The script:

- verifies the admin token is valid and has the `admin` role;
- creates or updates the bot user `rocket-admin-bot`;
- generates a personal access token for the bot;
- writes the skill-local `.env` (mode 600, gitignored);
- never writes the admin token to disk.

Verify at any time:

```bash
bash scripts/rc.sh GET /api/v1/me
```

The command should return `"username": "rocket-admin-bot"` and `"roles"` containing `admin`.

To reconfigure or rotate the bot token:

```bash
bash scripts/setup-bot.sh --force
```

## Tools

All paths are relative to this skill directory.

### `scripts/rc.sh` - authenticated API caller

```bash
bash scripts/rc.sh METHOD /api/path [--json '<body>'] [--data k=v ...]
```

Examples:

```bash
bash scripts/rc.sh GET  /api/v1/me
bash scripts/rc.sh GET  /api/v1/users.info username=nizarayed
bash scripts/rc.sh GET  /api/v1/users.list count=50 offset=0
bash scripts/rc.sh POST /api/v1/channels.create --json '{"name":"ops","members":["nizarayed"]}'
```

Behavior:

- `GET` args become URL-encoded query parameters.
- `POST` with `--json` sends a JSON body.
- `POST` without `--json` sends form fields from `--data`.
- Prints pretty JSON, then exits non-zero on HTTP 400+.
- Blocks hard deletes unless `RC_ALLOW_HARD_DELETE=1`.

### `scripts/rc-doc.sh` - live endpoint details

Use this whenever you need exact parameters, request bodies, or response shapes. It reads the live spec, not a stale local copy.

```bash
bash scripts/rc-doc.sh channels.create
bash scripts/rc-doc.sh users.list
bash scripts/rc-doc.sh POST /api/v1/channels.archive
bash scripts/rc-doc.sh --family roles
bash scripts/rc-doc.sh --list
bash scripts/rc-doc.sh channels.create --json   # raw operation JSON
```

Undocumented routes are flagged. Use `--documented-only` to hide them.

### `scripts/rc-index.sh` - regenerate the index

```bash
bash scripts/rc-index.sh
```

Fetches both the documented and full live specs and rewrites `references/api-index.md`. Undocumented routes are marked with a dagger (†).

### `scripts/setup-bot.sh` - one-time bot setup

See the setup section above.

## API index

The live spec has no `tags`, `summary`, or `operationId` fields. Families below are derived from path prefixes. The complete endpoint list is in [`references/api-index.md`](references/api-index.md).

### Families by operation count

| Family | Ops | Family | Ops |
|---|---:|---|---:|
| `livechat` | 147 | `roles` | 9 |
| `users` | 48 | `settings` | 9 |
| `channels` | 42 | `integrations` | 8 |
| `apps` | 40 | `calendar-events` | 6 |
| `groups` | 38 | `canned-responses` | 6 |
| `rooms` | 37 | `email-inbox` | 6 |
| `chat` | 29 | `sessions` | 6 |
| `omnichannel` | 19 | `audit` | 5 |
| `teams` | 19 | `commands` | 5 |
| `abac` | 15 | `custom-sounds` | 5 |
| `dm` | 15 | `emoji-custom` | 5 |
| `im` | 15 | `import` | 5 |
| `video-conference` | 15 | `oauth-apps` | 5 |
| `e2e` | 11 | `push` | 5 |
| `cloud` | 10 | `autotranslate` | 4 |
| `moderation` | 10 | `custom-user-status` | 4 |
| `engagement-dashboard` | 9 | `experimental` | 4 |
| `licenses` | 4 | `media-calls` | 4 |
| `permissions` | 4 | `subscriptions` | 4 |
| `ai` | 3 | `banners` | 3 |
| `ldap` | 3 | `statistics` | 3 |

Other families include `assets`, `call-history`, `directory`, `federation`, `instances`, `mailer`, `presence`, `saml`, `smtp`, `uploads`, `webdav`, and more. See the reference file for all 82 families.

### How to look up an endpoint

1. Find the family and action in `references/api-index.md`.
2. Run `bash scripts/rc-doc.sh <family>.<action>`.
3. Call it with `bash scripts/rc.sh`.

If a call returns HTTP 400, the live spec sometimes has incomplete parameter metadata (for example `rooms.info`). Check `rc-doc.sh --json <endpoint>` and the official docs, then try the conventional `roomId` or `roomName` parameter.

## Common admin operations

Placeholders such as `<userId>`, `<roomName>`, and `<username>` must be replaced.

### Identity and health

```bash
bash scripts/rc.sh GET /api/v1/me
bash scripts/rc.sh GET /api/v1/info
bash scripts/rc.sh GET /api/v1/statistics
```

### Users

```bash
# List and search (users.list is undocumented but present)
bash scripts/rc.sh GET /api/v1/users.list count=50 offset=0
bash scripts/rc.sh GET /api/v1/users.list 'query={"active":true}'
bash scripts/rc.sh GET /api/v1/users.list 'query={"roles":"admin"}'
bash scripts/rc.sh GET /api/v1/users.info username=<username>

# Create
bash scripts/rc.sh POST /api/v1/users.create --json '{
  "username":"<username>",
  "email":"<email>",
  "name":"<full name>",
  "password":"<password>",
  "roles":["user"],
  "verified":true
}'

# Update profile fields
bash scripts/rc.sh POST /api/v1/users.update --json '{
  "userId":"<userId>",
  "data":{"name":"<new name>","email":"<new email>"}
}'

# Logical delete: deactivate
bash scripts/rc.sh POST /api/v1/users.setActiveStatus --json '{
  "userId":"<userId>",
  "activeStatus":false
}'

# Reactivate
bash scripts/rc.sh POST /api/v1/users.setActiveStatus --json '{
  "userId":"<userId>",
  "activeStatus":true
}'

# Add a role
bash scripts/rc.sh POST /api/v1/roles.addUserToRole --json '{
  "username":"<username>",
  "roleId":"admin"
}'
```

### Channels (public rooms)

```bash
bash scripts/rc.sh GET  /api/v1/channels.list count=50 offset=0
bash scripts/rc.sh GET  /api/v1/channels.info roomName=<channel>
bash scripts/rc.sh POST /api/v1/channels.create --json '{
  "name":"<channel>",
  "members":["<username>"]
}'
bash scripts/rc.sh POST /api/v1/channels.invite --json '{
  "roomName":"<channel>",
  "username":"<username>"
}'
bash scripts/rc.sh POST /api/v1/channels.setTopic --json '{
  "roomName":"<channel>",
  "topic":"<topic>"
}'
bash scripts/rc.sh POST /api/v1/channels.addModerator --json '{
  "roomName":"<channel>",
  "username":"<username>"
}'

# Logical delete: archive (keeps history)
bash scripts/rc.sh POST /api/v1/channels.archive --json '{"roomName":"<channel>"}'

# Or close (hides from the room list)
bash scripts/rc.sh POST /api/v1/channels.close --json '{"roomName":"<channel>"}'
```

### Groups (private rooms)

```bash
bash scripts/rc.sh GET  /api/v1/groups.list
bash scripts/rc.sh GET  /api/v1/groups.info roomName=<group>
bash scripts/rc.sh POST /api/v1/groups.create --json '{
  "name":"<group>",
  "members":["<username>"]
}'
bash scripts/rc.sh POST /api/v1/groups.invite --json '{
  "roomName":"<group>",
  "username":"<username>"
}'

# Logical delete
bash scripts/rc.sh POST /api/v1/groups.archive --json '{"roomName":"<group>"}'
bash scripts/rc.sh POST /api/v1/groups.close --json '{"roomName":"<group>"}'
```

### Teams

```bash
bash scripts/rc.sh GET  /api/v1/teams.list
bash scripts/rc.sh GET  /api/v1/teams.info teamName=<team>
bash scripts/rc.sh POST /api/v1/teams.create --json '{
  "name":"<team>",
  "type":0,
  "members":["<username>"]
}'
bash scripts/rc.sh POST /api/v1/teams.addRooms --json '{
  "teamName":"<team>",
  "rooms":["<roomId>"]
}'
bash scripts/rc.sh GET  /api/v1/teams.members teamName=<team>
```

`type` is `0` for public and `1` for private. `teams.delete` is a hard delete; archive the team's rooms instead.

### Rooms

```bash
bash scripts/rc.sh GET  /api/v1/rooms.adminRooms count=50 offset=0
bash scripts/rc.sh GET  /api/v1/rooms.info roomId=<roomId>
bash scripts/rc.sh POST /api/v1/rooms.changeArchivationState --json '{
  "rid":"<roomId>",
  "action":"archive"
}'
```

### Roles and permissions

```bash
bash scripts/rc.sh GET  /api/v1/roles.list
bash scripts/rc.sh POST /api/v1/roles.create --json '{
  "name":"<role>",
  "description":"<description>",
  "scope":"Users"
}'
bash scripts/rc.sh GET  /api/v1/roles.getUsersInRole role=admin count=50
bash scripts/rc.sh GET  /api/v1/permissions.listAll
bash scripts/rc.sh POST /api/v1/permissions.update --json '{
  "permissions":[
    {"_id":"<permissionId>","roles":["admin","<role>"]}
  ]
}'
```

### Settings

```bash
bash scripts/rc.sh GET  /api/v1/settings count=100 offset=0
bash scripts/rc.sh GET  /api/v1/settings/Site_Url
bash scripts/rc.sh POST /api/v1/settings/Site_Url --json '{"value":"https://rocket.codimeo.com"}'
bash scripts/rc.sh GET  /api/v1/settings.public
```

### Messages

```bash
bash scripts/rc.sh POST /api/v1/chat.postMessage --json '{
  "roomId":"<roomId>",
  "text":"<message>"
}'
bash scripts/rc.sh GET  /api/v1/chat.getMessage msgId=<msgId>
bash scripts/rc.sh POST /api/v1/chat.pinMessage --json '{"messageId":"<msgId>"}'
```

`chat.delete` is a permanent delete and is blocked by default.

### Integrations and webhooks

```bash
bash scripts/rc.sh GET /api/v1/integrations.list count=50 offset=0
bash scripts/rc.sh GET /api/v1/integrations.history count=50
bash scripts/rc-doc.sh integrations.create
```

### Statistics and audit

```bash
bash scripts/rc.sh GET /api/v1/statistics
bash scripts/rc.sh GET /api/v1/statistics.list
bash scripts/rc.sh GET /api/v1/audit.settings
```

## Destructive operations policy

Hard deletes are blocked by default. This keeps data recoverable for a human to purge later.

| Target | Logical operation |
|---|---|
| User | `users.setActiveStatus` with `activeStatus:false` (deactivate) |
| Channel | `channels.archive` (keep history) or `channels.close` |
| Group | `groups.archive` or `groups.close` |
| Room | `rooms.changeArchivationState` with `action:"archive"` |
| Team | archive the team's rooms; `teams.delete` is permanent |
| Message | `chat.delete` is permanent; prefer editing or moderation |

Blocked patterns: `DELETE` requests, paths ending in `.delete`, and `integrations.remove`.

If a permanent delete is truly required, opt in explicitly for that one command:

```bash
RC_ALLOW_HARD_DELETE=1 bash scripts/rc.sh POST /api/v1/chat.delete --json '{
  "msgId":"<msgId>",
  "roomId":"<roomId>"
}'
```

Do not export `RC_ALLOW_HARD_DELETE` globally.

## Query, pagination, and errors

- Pagination is `count` and `offset`. Default count is often 50.
- `sort` and `query` take JSON strings. `rc.sh` URL-encodes them automatically.
  - `sort={"createdAt":-1}`
  - `query={"active":true}`
- `rc.sh` prints the JSON response, then exits non-zero on HTTP 400+.
- `401`: token invalid or missing. Run `rc.sh GET /api/v1/me`.
- `403`: the bot lacks the required role.
- `400`: validation error; inspect the `error` and `details` fields, then use `rc-doc.sh`.

## Server maintenance (optional)

The API covers administration. For container-level work, use SSH. The host defines a `RemoteCommand`, so non-interactive commands need overrides:

```bash
ssh -o RemoteCommand=none -o RequestTTY=no mac-ubuntu-server-2.local \
  'docker ps --filter name=rocketchat'

ssh -o RemoteCommand=none -o RequestTTY=no mac-ubuntu-server-2.local \
  'docker logs --tail 100 rocketchat-rocketchat-1'

ssh -o RemoteCommand=none -o RequestTTY=no mac-ubuntu-server-2.local \
  'cd ~/rocketchat && docker compose restart rocketchat'
```

Only touch the Rocket.Chat containers and compose project. Do not modify unrelated services.

## Troubleshooting

### Setup fails with `totp-required`

Rocket.Chat auto-enrolls new users in email 2FA when `Accounts_TwoFactorAuthentication_By_Email_Auto_Opt_In` is enabled. The bot only needs a password for the one-time login that generates its token, so disable email 2FA on the bot only.

On the Rocket.Chat host:

```bash
docker exec rocketchat-mongodb-1 mongosh --quiet --eval \
  'db.getSiblingDB("rocketchat").users.updateOne({username:"rocket-admin-bot"},{$set:{"services.email2fa.enabled":false}})'
```

Then rerun `bash scripts/setup-bot.sh`.

### Setup fails with a password policy error

The script generates a password with lowercase, uppercase, digits, and a special character. If your policy is stricter, adjust the character set or length in `scripts/setup-bot.sh`.

### `rc.sh` returns 401

Run `bash scripts/rc.sh GET /api/v1/me`. If it fails, rerun `bash scripts/setup-bot.sh --force` to rotate the bot token.

### `rc-doc.sh` cannot find an endpoint

Run `bash scripts/rc-doc.sh --list` to see families, or `bash scripts/rc-doc.sh --family <name>`. Some routes are undocumented; drop `--documented-only` or use the full spec, which is the default.

## Security rules

- Never print, echo, or paste the contents of `.env`.
- The bot token is an admin credential. Treat it like a password.
- Rotate it with `bash scripts/setup-bot.sh --force`.
- Do not put tokens in command arguments that may be logged. The scripts read them from `.env`.
- Do not run hard deletes without explicit user confirmation.

## References

- [`references/api-index.md`](references/api-index.md): full index of 693 operations across 82 families.
- Live spec: `https://rocket.codimeo.com/api/docs/json`
- Full spec: `https://rocket.codimeo.com/api/docs/json?withUndocumented=true`
- Swagger UI: `https://rocket.codimeo.com/api-docs`
- Official docs: `https://developer.rocket.chat`
