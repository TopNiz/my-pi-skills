#!/usr/bin/env bash
# verify.sh — Verify stored Freebox credentials WITHOUT re-authenticating
#
# Checks that the app token in the macOS keychain is valid by opening a
# session. It NEVER triggers the Freebox LCD authorization flow, so it is
# safe to run while the user is remote.
#
# Exit codes:
#   0  credentials valid (session token refreshed + stored in keychain)
#   1  missing credentials / unreachable box / other failure
#   2  stored app token is INVALID — re-auth requires LCD, STOP and ask user
set -euo pipefail

FBX_BASE=$(security find-generic-password -a "freebox" -s "freebox-api-base" -w 2>/dev/null || true)
APP_ID=$(security find-generic-password -a "freebox" -s "freebox-app-id" -w 2>/dev/null || true)
APP_TOKEN=$(security find-generic-password -a "freebox" -s "freebox-app-token" -w 2>/dev/null || true)

if [ -z "$FBX_BASE" ] || [ -z "$APP_ID" ] || [ -z "$APP_TOKEN" ]; then
  echo "❌ Missing keychain credentials (freebox-api-base / freebox-app-id / freebox-app-token)."
  echo "   ⛔ Do NOT request a new authorization automatically."
  echo "   ⛔ The app must be authorized on the Freebox LCD by someone with physical access."
  exit 1
fi

CHALLENGE=$(curl -sk --connect-timeout 10 "$FBX_BASE/login/" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['challenge'])" 2>/dev/null || true)
if [ -z "$CHALLENGE" ]; then
  echo "❌ Could not reach the Freebox at $FBX_BASE"
  exit 1
fi

PASSWORD=$(echo -n "$CHALLENGE" | openssl dgst -sha1 -hmac "$APP_TOKEN" | awk '{print $2}')
RESPONSE=$(curl -sk --connect-timeout 10 -X POST "$FBX_BASE/login/session/" \
  -H "Content-Type: application/json" \
  -d "{\"app_id\":\"$APP_ID\",\"password\":\"$PASSWORD\"}")

SUCCESS=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['success'])" 2>/dev/null || echo "False")

if [ "$SUCCESS" != "True" ]; then
  ERR=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error_code','?'))" 2>/dev/null || echo "?")
  echo "❌ Stored app token is INVALID (error_code: $ERR)"
  echo "   ⛔ Do NOT re-authenticate — re-authorization requires the Freebox LCD."
  echo "   ⛔ Ask the user for explicit confirmation before any authorize attempt."
  exit 2
fi

SESSION_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['session_token'])" 2>/dev/null)
PERMS=$(echo "$RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)['result']['permissions']
print(', '.join(k for k,v in d.items() if v))
" 2>/dev/null || true)

security add-generic-password -a "freebox" -s "freebox-session-token" -w "$SESSION_TOKEN" -U 2>/dev/null

echo "✅ Stored app token is VALID — session token refreshed (stored in keychain)."
echo "   ✅ No re-authentication needed — the Freebox LCD is NOT required."
[ -n "$PERMS" ] && echo "   Permissions: $PERMS"
