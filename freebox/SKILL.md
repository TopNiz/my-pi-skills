---
name: freebox
description: Full access to Freebox Server API (FreeboxOS) — connection status, Wi-Fi, LAN, downloads/torrents, file system, calls, contacts, voicemail, TV, system. Authenticates via app_token + HMAC-SHA1 session tokens stored in macOS keychain.
allowed-tools: Bash(curl:*) Bash(openssl:*) Bash(security:*) Bash(python3:*)
---

# Freebox Skill

Full API access to your Freebox Server via the FreeboxOS REST API.

## 📖 Offline Documentation

A complete copy of the official FreeboxOS API docs is available at `docs/*.html`.

**When to consult the docs**: fall back to reading the relevant doc file only when:
- The endpoint you need isn't documented in this SKILL.md
- You're unsure about request/response fields, parameters, or error codes
- You get an unexpected response and need the authoritative reference

**Documentation file map** (all paths relative to skill dir `~/.agents/skills/freebox/`):

| Feature | Doc file |
|---|---|
| Login, auth, sessions | `docs/login.html` |
| Connection, FTTH/xDSL stats | `docs/connection.html` |
| Wi-Fi APs, planning, guests | `docs/wifi.html` |
| LAN, DHCP, devices | `docs/lan.html` / `docs/dhcp.html` |
| NAT, port forwarding, UPnP IGD | `docs/nat.html` / `docs/igd.html` |
| Downloads, torrents, NZB | `docs/download.html` / `docs/download_config.html` / `docs/download_feeds.html` |
| File system (browse, upload, delete) | `docs/fs.html` / `docs/upload.html` |
| File sharing links | `docs/share.html` |
| Network shares, FTP | `docs/network_share.html` / `docs/ftp.html` |
| System, reboot, firmware | `docs/system.html` |
| Call logs | `docs/call.html` |
| Contacts | `docs/contacts.html` |
| PVR, TV recordings | `docs/pvr.html` |
| AirMedia | `docs/airmedia.html` |
| VPN server / client | `docs/vpn.html` / `docs/vpn_client.html` |
| Parental control | `docs/parental.html` |
| Storage, disks | `docs/storage.html` |
| Switch, Freeplugs, LCD | `docs/switch.html` / `docs/freeplug.html` / `docs/lcd.html` |
| UPnP AV | `docs/upnpav.html` |
| RRD statistics | `docs/rrd.html` |
| API version changes | `docs/api_changes_*_to_*.html` |
| Full TOC | `docs/index.html` |

---

| Credential | Keychain Entry | Purpose |
|---|---|---|
| App token | `freebox-app-token` | Long-lived app identity (one-time authorization) |
| Session token | `freebox-session-token` | Short-lived auth token (must be renewed) |
| App ID | `freebox-app-id` | Application identifier |
| API base URL | `freebox-api-base` | Base URL for API calls |

> **🔒 Security note**: All credentials are read exclusively from macOS keychain. Never echo, print, or pipe them through tools that output to stdout (e.g., avoid `python3 -m json.tool` on auth responses). Use `security find-generic-password -w` to source them directly into shell variables.

---

## Project Structure

```
freebox/
├── SKILL.md                    # This file
├── docs/                       # Offline API reference (from dev.freebox.fr)
│   ├── index.html              # Full TOC → start here
│   ├── login.html              # Authentication docs
│   ├── connection.html         # Connection & xDSL/FTTH stats
│   ├── download.html           # Torrent/download manager
│   ├── fs.html                 # File system
│   ├── wifi.html               # Wi-Fi configuration
│   ├── lan.html                # LAN & DHCP
│   ├── nat.html                # NAT & port forwarding
│   ├── system.html             # System & firmware
│   ├── call.html               # Call logs
│   ├── contacts.html           # Address book
│   ├── pvr.html                # TV recordings
│   ├── vpn.html / vpn_client.html
│   ├── parental.html           # Parental control
│   ├── storage.html            # Storage management
│   ├── airmedia.html           # AirMedia
│   ├── network_share.html      # Network shares
│   ├── ftp.html / upnpav.html / igd.html / lcd.html / rrd.html / switch.html / freeplug.html
│   ├── download_config.html / download_feeds.html
│   ├── upload.html / share.html
│   ├── api_changes_1_1_to_2_0.html / api_changes_2_0_to_3_0.html / api_changes_3_0_to_4_0.html
│   └── _static/                # CSS/JS assets
└── scripts/
    ├── login.sh                # Open a session (challenge → HMAC → session_token)
    ├── discover.sh             # Discover Freebox on local network
    └── call.sh                 # Make an authenticated API call
```

> **📖 Offline docs**: Open `docs/index.html` in a browser for the full API reference with sidebar navigation. All internal links are relative — works without internet.

---

## Quick Start

```bash
# Discover your Freebox on the network
bash ~/.agents/skills/freebox/scripts/discover.sh

# Open a session (stores session_token in keychain)
bash ~/.agents/skills/freebox/scripts/login.sh

# Make an authenticated call
bash ~/.agents/skills/freebox/scripts/call.sh GET /connection/
```

---

## Setup (One-Time Authorization)

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

# Save to keychain immediately — never display the token
security add-generic-password -a "freebox" -s "freebox-app-token" -w "$APP_TOKEN" -U
security add-generic-password -a "freebox" -s "freebox-app-id" -w "$APP_ID" -U
security add-generic-password -a "freebox" -s "freebox-api-base" -w "$FBX_BASE" -U

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

Once the app_token is in keychain, opening a session is a 3-step process.

> **🔑 All credentials come from keychain — never hardcoded or displayed.**

### Step 1: Get the challenge

```bash
FBX_BASE=$(security find-generic-password -a "freebox" -s "freebox-api-base" -w 2>/dev/null)
CHALLENGE=$(curl -sk "$FBX_BASE/login/" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['challenge'])")
```

### Step 2: Compute the HMAC-SHA1 password

```bash
APP_TOKEN=$(security find-generic-password -a "freebox" -s "freebox-app-token" -w 2>/dev/null)
PASSWORD=$(echo -n "$CHALLENGE" | openssl dgst -sha1 -hmac "$APP_TOKEN" | awk '{print $2}')
```

> **Formula**: `password = HMAC-SHA1(app_token, challenge)`

### Step 3: Open the session

```bash
APP_ID=$(security find-generic-password -a "freebox" -s "freebox-app-id" -w 2>/dev/null)

RESPONSE=$(curl -sk -X POST "$FBX_BASE/login/session/" \
  -H "Content-Type: application/json" \
  -d "{\"app_id\":\"$APP_ID\",\"password\":\"$PASSWORD\"}")

SUCCESS=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['success'])")

if [ "$SUCCESS" = "True" ]; then
  SESSION_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['session_token'])")
  PERMS=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin)['result']['permissions']; print(', '.join(k for k,v in d.items() if v))")
  
  # Save session token to keychain
  security add-generic-password -a "freebox" -s "freebox-session-token" -w "$SESSION_TOKEN" -U
  
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
FBX_BASE=$(security find-generic-password -a "freebox" -s "freebox-api-base" -w 2>/dev/null)
SESSION_TOKEN=$(security find-generic-password -a "freebox" -s "freebox-session-token" -w 2>/dev/null)

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

- **Session tokens expire** after a period of inactivity — if you get `auth_required` errors, re-run the login script
- **App tokens persist** unless the user revokes them from FreeboxOS or resets the admin password
- **Re-authorization** with the same `app_id` replaces the old token (old one becomes invalid)

### Logout

```bash
FBX_BASE=$(security find-generic-password -a "freebox" -s "freebox-api-base" -w 2>/dev/null)
SESSION_TOKEN=$(security find-generic-password -a "freebox" -s "freebox-session-token" -w 2>/dev/null)

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
