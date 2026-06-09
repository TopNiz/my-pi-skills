#!/usr/bin/env bash
# call.sh — Make an authenticated Freebox API call
# Usage: call.sh METHOD PATH [BODY]
#   call.sh GET /connection/
#   call.sh POST /downloads/add/ '{"url":"...","download_dir":"..."}'
set -euo pipefail

METHOD="${1:-GET}"
ENDPOINT="${2:-/connection/}"
BODY="${3:-}"

# ── Read credentials from keychain ──────────────────────────────
FBX_BASE=$(security find-generic-password -a "freebox" -s "freebox-api-base" -w 2>/dev/null)
SESSION_TOKEN=$(security find-generic-password -a "freebox" -s "freebox-session-token" -w 2>/dev/null)

if [ -z "$FBX_BASE" ] || [ -z "$SESSION_TOKEN" ]; then
  echo "❌ No active session. Run login.sh first."
  exit 1
fi

# ── Make the call ───────────────────────────────────────────────
TMPFILE=$(mktemp /tmp/fbx-response.XXXXXX)
HTTP_CODE=$(curl -sk -w "%{http_code}" -o "$TMPFILE" -X "$METHOD" "$FBX_BASE$ENDPOINT" \
  -H "X-Fbx-App-Auth: $SESSION_TOKEN" \
  ${BODY:+-H "Content-Type: application/json" -d "$BODY"})

# ── Check for auth errors in response ──────────────────────────
if echo "$HTTP_CODE" | grep -q "403"; then
  ERROR=$(python3 -c "import sys,json; d=json.load(open('$TMPFILE')); print(d.get('error_code','?'))" 2>/dev/null || echo "?")
  echo "❌ Auth error (403): $ERROR — try running login.sh"
  rm -f "$TMPFILE"
  exit 1
fi

# ── Pretty-print the response ──────────────────────────────────
python3 -m json.tool "$TMPFILE"
rm -f "$TMPFILE"
