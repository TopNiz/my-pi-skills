#!/usr/bin/env bash
# authorize.sh — Request Freebox app authorization and save app token securely.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

APP_ID="${FREEBOX_APP_ID:-fr.freebox.pi-agent}"
APP_NAME="${FREEBOX_APP_NAME:-pi coding agent}"
APP_VERSION="${FREEBOX_APP_VERSION:-1.0.0}"
DEVICE_NAME="${FREEBOX_DEVICE_NAME:-$(hostname -s 2>/dev/null || hostname)}"

FBX_BASE=$(secret_get "freebox-api-base" || true)
if [ -z "$FBX_BASE" ]; then
  echo "❌ Missing Freebox base URL. Run discover.sh first."
  exit 1
fi

RESPONSE=$(curl -sk -X POST "$FBX_BASE/login/authorize/" \
  -H "Content-Type: application/json" \
  -d "{\"app_id\":\"$APP_ID\",\"app_name\":\"$APP_NAME\",\"app_version\":\"$APP_VERSION\",\"device_name\":\"$DEVICE_NAME\"}")

SUCCESS=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('success'))" 2>/dev/null || echo False)
if [ "$SUCCESS" != "True" ]; then
  echo "❌ Authorization request failed"
  echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print('  error_code:', d.get('error_code','N/A')); print('  msg:', d.get('msg','N/A'))" 2>/dev/null || true
  exit 1
fi

TRACK_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['track_id'])")
APP_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['app_token'])")

secret_set "freebox-app-token" "$APP_TOKEN"
secret_set "freebox-app-id" "$APP_ID"

echo "✅ Authorization requested. Approve it on the Freebox LCD."
echo "   track_id: $TRACK_ID"
echo "   Polling status..."

for i in $(seq 1 60); do
  STATUS_RESPONSE=$(curl -sk "$FBX_BASE/login/authorize/$TRACK_ID")
  STATUS=$(echo "$STATUS_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['status'])" 2>/dev/null || echo unknown)
  echo "   status: $STATUS"
  case "$STATUS" in
    granted)
      echo "✅ Authorization granted. You can now run login.sh."
      exit 0
      ;;
    denied|timeout)
      echo "❌ Authorization $STATUS"
      exit 1
      ;;
  esac
  sleep 2
done

echo "❌ Authorization polling timed out"
exit 1
