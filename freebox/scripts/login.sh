#!/usr/bin/env bash
# login.sh — Open a Freebox API session
# Reads app_token and app_id from keychain, computes HMAC-SHA1, stores session_token in keychain
# NOTE: this script NEVER triggers the Freebox LCD authorization flow.
# If the stored app token is invalid, it exits with guidance — re-auth requires the LCD.
set -euo pipefail

# ── Read credentials from keychain ──────────────────────────────
FBX_BASE=$(security find-generic-password -a "freebox" -s "freebox-api-base" -w 2>/dev/null)
APP_ID=$(security find-generic-password -a "freebox" -s "freebox-app-id" -w 2>/dev/null)
APP_TOKEN=$(security find-generic-password -a "freebox" -s "freebox-app-token" -w 2>/dev/null)

if [ -z "$FBX_BASE" ] || [ -z "$APP_ID" ] || [ -z "$APP_TOKEN" ]; then
  echo "❌ Missing credentials in keychain."
  echo "   Run discover.sh first, then authorize the app (see SKILL.md Setup)."
  exit 1
fi

# ── Step 1: Get challenge ───────────────────────────────────────
CHALLENGE=$(curl -sk "$FBX_BASE/login/" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['challenge'])" 2>/dev/null)

if [ -z "$CHALLENGE" ]; then
  echo "❌ Failed to get challenge from Freebox"
  exit 1
fi

# ── Step 2: Compute HMAC-SHA1 password ──────────────────────────
PASSWORD=$(echo -n "$CHALLENGE" | openssl dgst -sha1 -hmac "$APP_TOKEN" | awk '{print $2}')

# ── Step 3: Open session ────────────────────────────────────────
RESPONSE=$(curl -sk -X POST "$FBX_BASE/login/session/" \
  -H "Content-Type: application/json" \
  -d "{\"app_id\":\"$APP_ID\",\"password\":\"$PASSWORD\"}")

SUCCESS=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['success'])" 2>/dev/null)

if [ "$SUCCESS" != "True" ]; then
  echo "❌ Session opening failed"
  echo "$RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"  error_code: {d.get('error_code', 'N/A')}\")
print(f\"  msg: {d.get('msg', 'N/A')}\")
" 2>/dev/null || echo "$RESPONSE"
  ERR=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('error_code',''))" 2>/dev/null || true)
  if [ "$ERR" = "invalid_token" ] || [ "$ERR" = "pending_token" ]; then
    echo ""
    echo "⛔ The stored app token is unusable — do NOT request a new authorization."
    echo "   Re-authorization requires the Freebox LCD (physical access)."
    echo "   Stop and ask the user for explicit confirmation first."
  fi
  exit 1
fi

# ── Extract and store session token ────────────────────────────
SESSION_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['session_token'])" 2>/dev/null)
PERMS=$(echo "$RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)['result']['permissions']
print(', '.join(k for k,v in d.items() if v))
" 2>/dev/null)

security add-generic-password -a "freebox" -s "freebox-session-token" -w "$SESSION_TOKEN" -U 2>/dev/null

echo "✅ Session opened"
echo "   Permissions: $PERMS"
