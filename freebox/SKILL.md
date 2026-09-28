---
name: freebox
description: Full access to Freebox Server API (FreeboxOS) — connection status, Wi-Fi, LAN, downloads/torrents, file system, calls, contacts, voicemail, TV, system. Authenticates via app_token + HMAC-SHA1 session tokens stored in the skill-local .env file.
allowed-tools: Bash(curl:*) Bash(openssl:*) Bash(python3:*)
---

# Freebox Skill

Full API access to your Freebox Server via the FreeboxOS REST API.

## 📖 Offline Documentation

`docs/index.html` is the **whole FreeboxOS API reference in a single page** (~1.8 MB),
vendored so it works offline.

| | |
|---|---|
| Source (on the box) | `https://<box>:40743/doc/index.html` |
| Vendored build | `c1fd8795` |
| Previously vendored | `9ba63963` (taken from `dev.freebox.fr/sdk/os/`) |
| Coverage | 2729 anchors across 69 endpoint families |

The box serves a **single-page** build: `docs/connection.html`, `docs/lan.html` etc. do not
exist there (all 404) — the older per-feature files were removed in favour of this one page.
The page also links to `genindex.html` and `search.html`, which the Freebox does not serve
either, so those two links are dead offline as well.

**Do not read the page wholesale.** Jump to a section by anchor:

```bash
cd ~/.agents/skills/freebox
grep -n 'id="dhcp-configuration-api"' docs/index.html          # find the line
awk '/id="dhcp-configuration-api"/,/id="dhcp-static-lease-api"/' docs/index.html   # extract it
```

**When to consult it**: the endpoint you need isn't covered below, you're unsure about
request/response fields, parameters or error codes, or a response was unexpected.

**Family anchors** — `docs/index.html#<anchor>`:

| Area | Anchor |
|---|---|
| Auth / session | `make-an-authenticated-call-to-the-api` |
| Connection, FTTH / xDSL / LTE | `connection-api` |
| LAN, devices, DHCP | `lan-config-api`, `lan-browser-api`, `dhcp-configuration-api`, `dhcp-static-lease-api`, `dhcpv6-configuration-api` |
| Wi-Fi | `wi-fi-global-config-api`, `wi-fi-ap-api`, `wi-fi-bss-api`, `wi-fi-mac-filter-api`, `wi-fi-steering-config-api`, `wifi-wps-api` |
| NAT, port forwarding, DMZ, UPnP-IGD | `port-forwarding-api`, `incoming-port-api`, `dmz-config-api`, `upnp-igd-config-api`, `upnp-igd-redirection-api` |
| Routing | `routing-config-api`, `rule-api` |
| Downloads, torrents | `download-api`, `download-files-api`, `download-tracker-api`, `download-feed-api` |
| File system | `file-system-api`, `file-sharing-link-api` |
| Shares: AFP / Samba / FTP / TFTP | `afp-config-api`, `samba-config-api`, `ftp-config-api`, `tftp-config-api` |
| Storage, disks, partitions | `storage-config-api`, `storage-disk-api`, `storage-partition-api` |
| System, firmware | `system-api` |
| Calls, voicemail, contacts | `call-api`, `voicemail-api`, `contact-api` |
| PVR, TV, media | `pvr-config-api`, `pvr-quota-api`, `media-api`, `frecord-api`, `precord-api` |
| AirMedia | `airmedia-api`, `airmedia-configuration-api` |
| VPN server | `vpn-server-config-api`, `vpn-server-connection-api`, `vpn-server-user-api` |
| Home automation / cameras | `home-api`, `camera-api` |
| Profiles, network control | `profiles-api`, `network-control-api` |
| Switch, Freeplug, LCD, LED strip | `switch-api`, `freeplug-api`, `lcd-config-api`, `ledstrip-api` |
| UPnP AV | `upnp-av-config-api` |
| Diagnostics | `diagnostic-api`, `slowness-api` |
| WebSocket | `websocket-api`, `websocket-event-api`, `websocket-file-upload-api`, `ws-api` |

### Refreshing the vendored docs

```bash
cd ~/.agents/skills/freebox
B="https://<box>:40743/doc"
for f in index.html _static/documentation_options.js _static/fbx.js \
         _static/main.css _static/pygments.css; do
  curl -sk --create-dirs -o "docs/$f" "$B/$f"
done
```

`_static/favicon.ico` is referenced by the page but not served by the box; the vendored
copy is kept so the reference resolves.

### Undocumented endpoints (`/domain/`, `/settings/`)

Two API families exist on v16 and are used by the FreeboxOS web UI, but appear in **no**
published doc set — not in this vendored build, not on `dev.freebox.fr`: **`/domain/`** and
**`/settings/`**. Do not conclude an endpoint is absent just because the docs omit it.

Found so far:

| Endpoint | Returns |
|---|---|
| `GET /domain/config/` | `default_domain`, `root_domains`, `api_domain` |
| `GET /domain/owned/` | domains with `type` (`auto` / `custom`) and per-algorithm cert status |
| `GET /settings/` | FreeboxOS desktop/app layout |
| `GET /settings/{1..15}` | per-app UI state, including window geometry |

**How they were discovered — the reliable method for this box.** The FreeboxOS UI hash names
the API family directly. Open the settings pane in a browser and read the hash:

```
#Fbx.os.app.settings.domains.Domains   →  /domain/config/, /domain/owned/
```

Then confirm via the page's own request log rather than guessing paths:

```js
performance.getEntriesByType('resource')
  .map(r => r.name).filter(n => /\/api\//.test(n))
```

> ⚠️ **A browser login evicts the skill's API session.** Opening FreeboxOS in a browser
> while the skill is authenticated makes the next `call.sh` return `403`, even immediately
> after `verify.sh` refreshed the token (FreeboxOS limits concurrent sessions). To keep
> working, query the API from inside the logged-in page:
> `fetch('/api/latest/settings/', {credentials: 'include'})`. Note the UI uses
> `/api/latest/`, which also works through `call.sh`.

---

| Credential | `.env` variable | Purpose |
|---|---|---|
| App token | `FREEBOX_APP_TOKEN` | Long-lived app identity (one-time authorization) |
| Session token | `FREEBOX_SESSION_TOKEN` | Short-lived auth token (must be renewed) |
| App ID | `FREEBOX_APP_ID` | Application identifier |
| API base URL | `FREEBOX_API_BASE` | Base URL for API calls |

> **🔒 Security note**: Credentials are stored only in `~/.agents/skills/freebox/.env`, which must be owner-readable only (`chmod 600`). Never echo, print, commit, or share this file or its values. The helper scripts load it without requiring a macOS keychain, making them suitable for remote shells.

> **🚨 MANDATORY — Verify before you authenticate**: Before ANY authentication request (or when any API call fails with `auth_required` / `invalid_token` / `pending_token`), **first verify the stored token** with `scripts/verify.sh`. If the stored token is valid, **do NOT re-authenticate** — never run the Setup/authorize flow. The user may be remote with no access to the Freebox LCD. Only request a new authorization after the user explicitly confirms they can physically approve on the LCD.

---

## Project Structure

```
freebox/
├── .env                        # Owner-only API credentials (never commit/share)
├── SKILL.md                    # This file
├── docs/                       # API reference, generated by the Freebox itself
│   ├── index.html              # The whole API in one page (~1.8 MB)
│   └── _static/                # CSS/JS assets
└── scripts/
    ├── login.sh                # Open a session (challenge → HMAC → session_token)
    ├── discover.sh             # Discover Freebox on local network
    └── call.sh                 # Make an authenticated API call
```

> **📖 Offline docs**: `docs/index.html` holds the entire API in one page — it is the
> authoritative reference for request/response fields. It is a flat single-page build (no
> sidebar, and its `genindex.html` / `search.html` links 404 on the box too), so navigate it
> by anchor or extract a single section rather than reading the whole file.

---

## Quick Start

```bash
# 1. VERIFY the stored app token (SAFE — never touches the Freebox LCD)
bash ~/.agents/skills/freebox/scripts/verify.sh

# 2. If valid → open a session (uses the stored .env token only, no LCD needed)
bash ~/.agents/skills/freebox/scripts/login.sh

# 3. Make an authenticated call
bash ~/.agents/skills/freebox/scripts/call.sh GET /connection/
```

---

## ✅ Verify Stored Credentials First (MANDATORY)

**Before any authentication request — or whenever any API call fails with `auth_required` / `invalid_token` / `pending_token` — follow this order:**

1. **Check for an existing app token in the skill-local `.env`:**
   ```bash
   test -r ~/.agents/skills/freebox/.env && \
     grep -q '^FREEBOX_APP_TOKEN=' ~/.agents/skills/freebox/.env && \
     echo "token present" || echo "token missing"
   ```
2. **If present, verify it is valid** (this NEVER touches the LCD — it only opens a session with the stored token):
   ```bash
   bash ~/.agents/skills/freebox/scripts/verify.sh
   ```
3. **If the token is valid → STOP. Do NOT request a new authorization. Do NOT run the Setup flow below.** The user may be remote and cannot approve on the Freebox LCD. Proceed with the API (verify.sh refreshes the session token automatically).
4. **Only if the token is missing OR invalid (`invalid_token` / `pending_token`) → STOP and ask the user explicitly** before running the Setup flow. Re-authentication requires physical access to the Freebox LCD — never do it automatically.

---

## Setup (One-Time Authorization)

> ⚠️ **This flow requires physical access to the Freebox LCD screen. Only run it when:**
> 1. No valid `FREEBOX_APP_TOKEN` exists in `.env` **AND** the user has confirmed they can physically approve on the LCD, **or**
> 2. The user explicitly instructs you to re-authenticate.
>
> **Never run this flow automatically as a fallback.** If the stored token is invalid, stop and ask the user first.

Before using the API, your app must be authorized on the Freebox. This requires physical access to the Freebox LCD screen.

### 1. Discover the Freebox

```bash
curl -sk https://mafreebox.freebox.fr/api_version
```

Response example:
```json
{
  "api_version": "15.0",
  "api_base_url": "/api/",
  "api_domain": "6aq4jkyq.fbxos.fr",
  "https_port": 40743,
  "uid": "beb2aefbd0f1535c986bea28a8f33a11",
  "device_type": "FreeboxServer7,1",
  "https_available": true
}
```

### 2. Build the base URL

```
https://[api_domain]:[https_port][api_base_url]v[major_api_version]
```

Where `major_api_version` is the integer part of `api_version` (e.g., `15` from `15.0`).

Example:
```bash
FBX_BASE="https://6aq4jkyq.fbxos.fr:40743/api/v15"
```

### 3. Request app authorization

This triggers a prompt on the Freebox LCD. The user must physically approve it.

```bash
APP_ID="fr.freebox.myapp"
APP_NAME="My App"
APP_VERSION="1.0.0"
DEVICE_NAME="$(hostname -s)"

RESPONSE=$(curl -sk -X POST "$FBX_BASE/login/authorize/" \
  -H "Content-Type: application/json" \
  -d "{\"app_id\":\"$APP_ID\",\"app_name\":\"$APP_NAME\",\"app_version\":\"$APP_VERSION\",\"device_name\":\"$DEVICE_NAME\"}")

# ⚠️ NEVER print RESPONSE directly — it contains the app_token
# Extract only what you need:
TRACK_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['track_id'])")
APP_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['app_token'])")

# Save to the skill-local .env immediately — never display the token
source ~/.agents/skills/freebox/scripts/common.sh
secret_set "freebox-app-token" "$APP_TOKEN"
secret_set "freebox-app-id" "$APP_ID"
secret_set "freebox-api-base" "$FBX_BASE"

echo "track_id=$TRACK_ID — approve on Freebox LCD"
```

### 4. Poll authorization status

Wait for the user to approve on the Freebox LCD:

```bash
for i in $(seq 1 60); do
  RESPONSE=$(curl -sk "$FBX_BASE/login/authorize/$TRACK_ID")
  STATUS=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['status'])")
  echo "Status: $STATUS"
  if [ "$STATUS" != "pending" ]; then
    break
  fi
  sleep 2
done
```

Status values: `pending` → `granted` | `denied` | `timeout`

---

## Login — Opening a Session

Once the app token is in the skill-local `.env`, opening a session is a 3-step process.

> **🔑 All credentials come from the skill-local `.env` — never hardcoded or displayed.**

### Step 1: Get the challenge

```bash
source ~/.agents/skills/freebox/.env
FBX_BASE="$FREEBOX_API_BASE"
CHALLENGE=$(curl -sk "$FBX_BASE/login/" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['challenge'])")
```

### Step 2: Compute the HMAC-SHA1 password

```bash
APP_TOKEN="$FREEBOX_APP_TOKEN"
PASSWORD=$(echo -n "$CHALLENGE" | openssl dgst -sha1 -hmac "$APP_TOKEN" | awk '{print $2}')
```

> **Formula**: `password = HMAC-SHA1(app_token, challenge)`

### Step 3: Open the session

```bash
APP_ID="$FREEBOX_APP_ID"

RESPONSE=$(curl -sk -X POST "$FBX_BASE/login/session/" \
  -H "Content-Type: application/json" \
  -d "{\"app_id\":\"$APP_ID\",\"password\":\"$PASSWORD\"}")

SUCCESS=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['success'])")

if [ "$SUCCESS" = "True" ]; then
  SESSION_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['session_token'])")
  PERMS=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin)['result']['permissions']; print(', '.join(k for k,v in d.items() if v))")
  
  # Save session token to the skill-local .env
  source ~/.agents/skills/freebox/scripts/common.sh
  secret_set "freebox-session-token" "$SESSION_TOKEN"
  
  echo "✅ Session opened — permissions: $PERMS"
else
  echo "❌ Session opening failed"
  echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print('error:', d.get('error_code'), '-', d.get('msg'))"
fi
```

### Full login script

See `scripts/login.sh` for the complete flow.

---

## Authenticated API Calls

All authenticated calls require the `X-Fbx-App-Auth` header with the session token:

```bash
source ~/.agents/skills/freebox/.env
FBX_BASE="$FREEBOX_API_BASE"
SESSION_TOKEN="$FREEBOX_SESSION_TOKEN"

curl -sk "$FBX_BASE/connection/" \
  -H "X-Fbx-App-Auth: $SESSION_TOKEN"
```

### Call helper

See `scripts/call.sh`:
```bash
bash ~/.agents/skills/freebox/scripts/call.sh GET /connection/
bash ~/.agents/skills/freebox/scripts/call.sh GET /system/
bash ~/.agents/skills/freebox/scripts/call.sh GET /downloads/
```

---

## Session Lifecycle

- **Session tokens expire** after a period of inactivity — if you get `auth_required` errors, run `verify.sh` then `login.sh` (both use the stored `.env` app token only; the LCD is never needed). `call.sh` also refreshes the session automatically in this case.
- **App tokens persist** unless the user revokes them from FreeboxOS or resets the admin password
- **Never re-authenticate automatically.** Re-authorization with the same `app_id` replaces the old token and **requires physical access to the Freebox LCD**. Only do it after explicit user confirmation.

### Logout

```bash
source ~/.agents/skills/freebox/.env
FBX_BASE="$FREEBOX_API_BASE"
SESSION_TOKEN="$FREEBOX_SESSION_TOKEN"

curl -sk -X POST "$FBX_BASE/login/logout/" \
  -H "X-Fbx-App-Auth: $SESSION_TOKEN"
```

---

## Authentication Errors

| Error code | Meaning |
|---|---|
| `auth_required` | Invalid or missing session token |
| `invalid_token` | App token invalid or revoked |
| `pending_token` | App token not yet validated by user |
| `insufficient_rights` | Your app permissions don't allow this API |
| `denied_from_external_ip` | Authorization only works from local network |
| `ratelimited` | Too many auth errors from your IP |
| `new_apps_denied` | New app token requests disabled on Freebox |
| `apps_denied` | API access from apps disabled |
| `internal_error` | Internal Freebox error |

> **On `invalid_token` / `pending_token`**: the stored app token is unusable. **STOP — do not run the authorize flow.** Report to the user; re-authentication is only possible from the local network with physical access to the Freebox LCD.

---

## App Permissions

Returned when opening a session:

| Permission | Description |
|---|---|
| `settings` | Modify Freebox settings (read is always allowed) |
| `contacts` | Access contact list |
| `calls` | Access call logs |
| `explorer` | Access file system |
| `downloader` | Access download/torrent manager |
| `parental` | Access parental control |
| `pvr` | Access personal video recorder |
| `tv` | Access TV features |
| `vm` | Access voicemail |
| `camera` | Access camera |
| `home` | Access home automation |
| `wdo` | Access connected objects |
| `player` | Access media player |
| `profile` | Access user profiles |

---

## DNS Configuration

DNS servers are managed through the DHCP config API. The Freebox hands out DNS servers to LAN clients via DHCP.

> **Docs**: `docs/dhcp.html` — full `DhcpConfig` object reference with all fields and error codes.

### Read current DNS

```bash
bash ~/.agents/skills/freebox/scripts/call.sh GET /dhcp/config/
```

The `result.dns` field is an array of up to 6 DNS server IPs. Empty strings mean no server at that slot.

**Example response** (relevant fields):
```json
{
  "success": true,
  "result": {
    "enabled": true,
    "gateway": "192.168.0.254",
    "netmask": "255.255.255.0",
    "dns": ["192.168.0.254", "8.8.8.8", "", "", "", ""],
    "ip_range_start": "192.168.0.10",
    "ip_range_end": "192.168.0.50",
    "sticky_assign": true
  }
}
```

### Update DNS servers

```bash
# Set DNS 1 = Freebox, DNS 2 = Cloudflare
bash ~/.agents/skills/freebox/scripts/call.sh PUT /dhcp/config/ \
  '{"dns":["192.168.0.254","1.1.1.1"]}'

# Reset to Freebox only
bash ~/.agents/skills/freebox/scripts/call.sh PUT /dhcp/config/ \
  '{"dns":["192.168.0.254"]}'

# Set multiple (Freebox + Cloudflare + Google + Quad9)
bash ~/.agents/skills/freebox/scripts/call.sh PUT /dhcp/config/ \
  '{"dns":["192.168.0.254","1.1.1.1","8.8.8.8","9.9.9.9"]}'
```

⚠️ **The DNS change is partial** — you only need to send the `dns` field. Other DHCP settings (enabled, gateway, IP range, etc.) are left unchanged.

### DHCP static leases

For completeness, the DHCP API also manages static leases and dynamic leases:

| Action | Method | Endpoint |
|---|---|---|
| List static leases | `GET` | `/dhcp/static_lease/` |
| Get one static lease | `GET` | `/dhcp/static_lease/{mac}` |
| Add static lease | `POST` | `/dhcp/static_lease/` |
| Update static lease | `PUT` | `/dhcp/static_lease/{mac}` |
| Delete static lease | `DELETE` | `/dhcp/static_lease/{mac}` |
| List dynamic leases | `GET` | `/dhcp/dynamic_lease/` |

---

## API Reference

**Offline**: Open `docs/index.html` in any browser — full API reference with sidebar TOC.

**Online**: `https://dev.freebox.fr/sdk/os/`

### API conventions

- All responses are JSON with `{success, result, error_code?, msg?}`
- HTTP methods: GET (read), POST (create/action), PUT (update), DELETE (remove)
- UTF-8 encoding
- HTTPS required (Freebox-issued certificates with custom CA)

### Endpoints overview

| Category | Base path | Description |
|---|---|---|
| Connection | `/connection/` | Status, FTTH/xDSL stats, port forwarding |
| System | `/system/` | Reboot, firmware, config |
| Wi-Fi | `/wifi/` | APs, planning, guest networks |
| LAN | `/lan/` | Interfaces, DHCP, devices |
| Downloads | `/downloads/` | Torrents, NZB, files, categories |
| File System | `/fs/` | Browse, upload, download, rename, delete |
| Calls | `/call/` | Call logs |
| Contacts | `/contact/` | Address book |
| Voicemail | `/vm/` | Voicemail messages |
| TV | `/tv/` | TV features |
| PVR | `/pvr/` | Recordings |
| WebSocket | `ws://...` | Real-time bidirectional events |
