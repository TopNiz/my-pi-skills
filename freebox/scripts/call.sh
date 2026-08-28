#!/usr/bin/env bash
# call.sh — Make an authenticated Freebox API call
# Usage: call.sh METHOD PATH [BODY]
#   call.sh GET /connection/
#   call.sh POST /downloads/add/ '{"url":"...","download_dir":"..."}'
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

METHOD="${1:-GET}"
ENDPOINT="${2:-/connection/}"
BODY="${3:-}"

# ── Read credentials from OS secret store ───────────────────────
FBX_BASE=$(secret_get "freebox-api-base" || true)
SESSION_TOKEN=$(secret_get "freebox-session-token" || true)

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
  rm -f "$TMPFILE"
  if [ "$ERROR" = "auth_required" ]; then
    # Session token expired — refresh it using the STORED app token (no LCD involved)
    echo "ℹ️  Session token expired ($ERROR) — refreshing from stored keychain token (no LCD needed)..."
    if bash "$(dirname "$0")/login.sh" >/dev/null 2>&1; then
      SESSION_TOKEN=$(security find-generic-password -a "freebox" -s "freebox-session-token" -w 2>/dev/null)
      TMPFILE=$(mktemp /tmp/fbx-response.XXXXXX)
      HTTP_CODE=$(curl -sk -w "%{http_code}" -o "$TMPFILE" -X "$METHOD" "$FBX_BASE$ENDPOINT" \
        -H "X-Fbx-App-Auth: $SESSION_TOKEN" \
        ${BODY:+-H "Content-Type: application/json" -d "$BODY"})
      if [ "$HTTP_CODE" != "403" ]; then
        python3 -m json.tool "$TMPFILE"
        rm -f "$TMPFILE"
        exit 0
      fi
      rm -f "$TMPFILE"
    fi
    echo "❌ Could not refresh the session from the stored token."
    bash "$(dirname "$0")/verify.sh" || true
    exit 1
  fi
  echo "❌ Auth error (403): $ERROR"
  echo "   ⛔ Do NOT request a new authorization automatically."
  echo "   Re-authorization requires the Freebox LCD — ask the user first."
  exit 1
fi

# ── Pretty-print the response ──────────────────────────────────
python3 -m json.tool "$TMPFILE"
rm -f "$TMPFILE"
