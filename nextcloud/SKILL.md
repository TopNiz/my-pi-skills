---
name: nextcloud
description: Expert Nextcloud administration with the `occ` command line. Use when the user asks to inspect, configure, repair, maintain, migrate, troubleshoot, or automate a Nextcloud instance using `occ`.
---

# Nextcloud `occ` Administration

Use this skill for safe, expert operation of Nextcloud's command-line administration tool, `occ`.

## Deployment types

This skill focuses on the `occ` commands themselves — what to run and why. It does **not** handle connectivity.

Nextcloud can run in different ways, and each affects how you invoke `occ`:

- **Docker Compose** (most common for AIO/managed setups) — use `docker compose exec` or `docker exec` into the container:
  ```bash
  docker compose exec -u www-data app php occ status
  docker exec -u www-data nextcloud-aio-nextcloud php occ status
  ```
- **Docker standalone** — same pattern, just target the container by name.
- **Native install** (bare metal, apt, manual) — run `occ` directly as the web server user:
  ```bash
  sudo -u www-data php /var/www/nextcloud/occ status
  ```
- **Snap package** — use the `nextcloud.occ` wrapper:
  ```bash
  sudo nextcloud.occ status
  ```

For **remote servers**, `ssh-skills` provides the connection layer (SSH, tunnels, file transfer). The typical workflow is: SSH into the server → identify the deployment type → run the appropriate `occ` command.

## Prime directive

Treat `occ` as an administrative interface to live application state. Before changing anything:

1. Identify the installation path, runtime user, PHP binary, and deployment type.
2. Prefer read-only discovery commands first.
3. Explain destructive or high-impact operations before running them.
4. Back up database/files/config before migrations, repairs, app changes, or bulk user/file operations.
5. Never run `occ` as root unless the deployment explicitly requires it; normally run it as the web-server/container user.

## Locate and invoke `occ`

Common locations:

```bash
/var/www/nextcloud/occ
/var/www/html/occ
/srv/www/nextcloud/occ
```

Find it:

```bash
sudo find /var/www /srv /opt -maxdepth 4 -name occ -type f 2>/dev/null
```

Native package/source install:

```bash
cd /path/to/nextcloud
sudo -u www-data php occ status
sudo -u www-data php occ list
```

If the web user differs, detect it from the web server/PHP-FPM config or file ownership:

```bash
stat -c '%U:%G %n' config/config.php occ
ps aux | grep -E 'php-fpm|apache|nginx' | grep -v grep
```

Docker Compose examples:

```bash
docker compose ps
docker compose exec -u www-data app php occ status
docker compose exec app php occ status
```

Snap package:

```bash
sudo nextcloud.occ status
```

Alias pattern after confirming the environment:

```bash
OCC='sudo -u www-data php /var/www/nextcloud/occ'
$OCC status
```

## Discovery checklist

Run these before diagnosing or changing state:

```bash
$OCC status
$OCC config:system:get version
$OCC config:system:get installed
$OCC list
$OCC app:list
$OCC maintenance:mode
$OCC config:list system --private=false
$OCC db:add-missing-indices --dry-run
$OCC db:add-missing-primary-keys --dry-run
$OCC db:add-missing-columns --dry-run
```

Also inspect logs and config directly when needed:

```bash
tail -n 200 /path/to/nextcloud/data/nextcloud.log
php -i | grep -E 'memory_limit|opcache|apcu|imagick|redis|pgsql|mysql'
```

## Maintenance mode

Use maintenance mode around risky operations:

```bash
$OCC maintenance:mode --on
$OCC maintenance:mode --off
$OCC maintenance:repair
```

Always verify it is turned off at the end unless intentionally left on:

```bash
$OCC maintenance:mode
```

## Upgrades and repairs

For CLI upgrade:

```bash
$OCC status
$OCC upgrade
$OCC maintenance:repair
$OCC db:add-missing-indices
$OCC db:add-missing-primary-keys
$OCC db:add-missing-columns
$OCC status
```

If upgrade is stuck, inspect logs and only then consider:

```bash
$OCC maintenance:mode --off
$OCC upgrade
```

Do not blindly edit `config.php` version values or app states.

## Apps

List and manage apps:

```bash
$OCC app:list
$OCC app:enable <app_id>
$OCC app:disable <app_id>
$OCC app:update --all
$OCC app:remove <app_id>
```

Before disabling/removing apps, check dependencies and user impact. For broken apps after an upgrade, prefer disabling only the offending app, then re-run upgrade/repair.

## Configuration

Read config:

```bash
$OCC config:system:get trusted_domains
$OCC config:system:get overwrite.cli.url
$OCC config:app:get <app> <key>
```

Set config with correct type:

```bash
$OCC config:system:set trusted_domains 1 --value=cloud.example.com
$OCC config:system:set overwrite.cli.url --value=https://cloud.example.com
$OCC config:system:set default_phone_region --value=US
$OCC config:system:set maintenance_window_start --type=integer --value=1
$OCC config:system:set memcache.local --value='\\OC\\Memcache\\APCu'
$OCC config:system:set redis host --value=/run/redis/redis-server.sock
$OCC config:system:set redis port --type=integer --value=0
```

Use `--type=boolean`, `--type=integer`, or `--type=json` where appropriate. Avoid editing `config/config.php` manually unless `occ` is unavailable.

## Users and groups

```bash
$OCC user:list
$OCC user:info <uid>
$OCC user:add <uid>
$OCC user:delete <uid>
$OCC user:disable <uid>
$OCC user:enable <uid>
$OCC user:resetpassword <uid>
$OCC group:list
$OCC group:add <group>
$OCC group:adduser <group> <uid>
$OCC group:removeuser <group> <uid>
```

For bulk operations, script defensively: quote user IDs, dry-run where possible, and log changes.

## Files, scans, and trash

Rescan files after out-of-band filesystem changes:

```bash
$OCC files:scan <uid>
$OCC files:scan --all
$OCC files:scan-app-data
```

Use narrower scans first; `--all` can be expensive.

Cleanup and versions/trash:

```bash
$OCC trashbin:cleanup --all-users
$OCC versions:cleanup
```

External storage:

```bash
$OCC files_external:list
$OCC files_external:verify <mount_id>
$OCC files_external:import <file.json>
$OCC files_external:export <file.json>
```

## Background jobs and cron

Check configured mode:

```bash
$OCC background:cron
$OCC config:system:get backgroundjobs_mode
```

Set cron mode:

```bash
$OCC background:cron
```

System cron should typically run every 5 minutes as the web user:

```cron
*/5 * * * * php -f /path/to/nextcloud/cron.php
```

## Database and integrity

Common safe checks:

```bash
$OCC integrity:check-core
$OCC integrity:check-app <app_id>
$OCC db:convert-filecache-bigint --dry-run
$OCC db:convert-filecache-bigint
```

Run schema-changing commands during maintenance windows and after backups.

## Indexation status

Check the health of the file cache, search indexes, and AI/Context Chat indexing.

### 1. File cache indexation (oc_filecache)

Run an unscanned scan across all users (idempotent, read-only):

```bash
$OCC files:scan --all --unscanned
```

Healthy signal: returns "0 new, 0 updated, 0 errors" and 0 seconds elapsed.
Files with `size = -1` are not fully scanned (preview thumbnails still generating is normal).

### 2. Fulltextsearch index

Check the fulltextsearch platform health and queue:

```bash
$OCC fulltextsearch:check
$OCC fulltextsearch:index                         # interactive — shows progress per user
$OCC fulltextsearch:stop                          # kill a running index process
$OCC fulltextsearch:reset                         # reset index (use with caution)
```

Check indexed document count directly via database:

```bash
# PostgreSQL
psql -d nextcloud_database -c "SELECT count(*) FROM oc_fulltextsearch_index;"

# MySQL/MariaDB
mysql nextcloud_database -e "SELECT count(*) FROM oc_fulltextsearch_index;"
```

Common issues:
- `ClientResponseException` from Elasticsearch → corrupted document in the index. Remove it:
  ```bash
  $OCC fulltextsearch:document:delete "Files" "files:<doc_id>"
  ```
- Deck app `TypeError: findBoardId() Argument #1 ($id) must be of type int, string given` → deck card share with string ID. Either disable the Deck content provider or patch the share data.
  ```bash
  # Disable deck content provider from fulltextsearch:
  $OCC fulltextsearch:configure {app_navigation:0} -p deck
  ```

### 3. Context Chat / AI indexation

Stats about files eligible for the AI backend:

```bash
$OCC context_chat:stats
```

Key metrics in the output:
- **Total eligible files** — all indexable files on disk
- **Files in indexing queue** — waiting to be processed
- **Files successfully sent to backend** — handed to the LLM backend
- **Indexed documents** — actually embedded and searchable (check `files__default` count)
- **Actions in queue / FS events in queue** — should be 0 when healthy

One-shot DB summary (PostgreSQL):

```bash
psql -d nextcloud_database -c "
SELECT 'Eligible (not in queue)' as metric, count(DISTINCT f.fileid)
FROM oc_filecache f
WHERE f.path NOT LIKE 'appdata_%%'
  AND f.mimetype > 0 AND f.storage > 1
  AND f.fileid NOT IN (SELECT file_id FROM oc_context_chat_queue)
UNION ALL
SELECT 'In indexing queue', count(*) FROM oc_context_chat_queue
UNION ALL
SELECT 'Actions in queue', count(*) FROM oc_context_chat_action_queue
UNION ALL
SELECT 'FS events in queue', count(*) FROM oc_context_chat_fs_events;
"
```

Common issues:
- Indexing stuck or very slow → check the LLM backend container logs
- Content queue empty but files still in queue → backend may be overwhelmed; check container resources

### 4. Database-level deep checks

Check for files with missing metadata (PostgreSQL / MySQL):

```sql
-- Unscanned files (not including appdata/previews)
SELECT count(*) as user_unscanned
FROM oc_filecache
WHERE (size = -1 OR size IS NULL)
  AND path NOT LIKE 'appdata_%%';

-- Missing mimetypes
SELECT count(*) as missing_mimetype
FROM oc_filecache
WHERE mimetype IS NULL OR mimetype = 0;

-- Missing etags
SELECT count(*) as missing_etag
FROM oc_filecache
WHERE etag IS NULL;

-- Files per storage (detect orphaned or wrong storage)
SELECT storage, count(*) as files
FROM oc_filecache
GROUP BY storage ORDER BY files DESC;
```

Healthy baseline: 0 missing mimetypes, 0 missing etags, unscanned count ≤ 25 (preview cache only).

### 5. Preview generation issues

Previews with size = -1 are normal during generation, but if the count is persistently high (>100):

```bash
# Force preview generation for a specific user
$OCC files:scan --generate-metadata --all
```

### Quick one-shot health check

```bash
$OCC status && \
$OCC files:scan --all --unscanned 2>&1 | tail -1 && \
$OCC context_chat:stats 2>&1 | grep -E "eligible|queue|sent|indexed|Actions|events"
```

## Encryption and LDAP caution

Encryption and LDAP commands can lock users out or make data inaccessible if mishandled. First gather status/config:

```bash
$OCC encryption:status
$OCC ldap:show-config
$OCC ldap:test-config <configID>
```

Do not enable/disable encryption, decrypt all files, or alter LDAP mappings without an explicit plan and backups.

## Troubleshooting patterns

- `This version of Nextcloud is not compatible with PHP`: use the PHP binary matching the installed Nextcloud version.
- `Console has to be executed with the user that owns the file config/config.php`: switch to the owner shown by `stat config/config.php`.
- `Memcache \OC\Memcache\APCu not available for local cache`: ensure PHP CLI has APCu enabled and `apc.enable_cli=1` for CLI commands that need it.
- Permission problems: fix ownership/permissions deliberately; do not recursive `chmod 777`.
- White page/500 after app install: inspect `data/nextcloud.log`, disable the problematic app with `app:disable`, then repair.

## References

### Ollama Cloud Models availability

See [references/ollama-cloud-models.md](references/ollama-cloud-models.md) for an up-to-date listing of free vs. paid cloud models on the Ollama server at `82.64.122.51:11434`, used by the `integration_openai` app on codimeo.com.

## Response style when using this skill

- State the exact `occ` invocation style selected, e.g. `sudo -u www-data php /var/www/nextcloud/occ`.
- Distinguish read-only checks from changes.
- For risky commands, ask for confirmation unless the user explicitly requested execution.
- End with verification commands and expected healthy signals.
