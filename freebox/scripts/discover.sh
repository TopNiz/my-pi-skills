#!/usr/bin/env bash
# discover.sh — Discover Freebox on the local network
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

echo "Discovering Freebox on local network..."

# Try HTTPS first, then HTTP
RESPONSE=$(curl -sk --connect-timeout 5 https://mafreebox.freebox.fr/api_version 2>/dev/null || \
           curl -s --connect-timeout 5 http://mafreebox.freebox.fr/api_version 2>/dev/null)

if [ -z "$RESPONSE" ]; then
  echo "❌ No Freebox found on the network"
  exit 1
fi

SUCCESS=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('success', True))" 2>/dev/null || echo "True")

if [ "$SUCCESS" != "True" ]; then
  echo "❌ Invalid response from Freebox"
  echo "$RESPONSE"
  exit 1
fi

# Extract fields
API_VERSION=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['api_version'])")
API_DOMAIN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['api_domain'])")
HTTPS_PORT=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['https_port'])")
API_BASE_URL=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['api_base_url'])")
DEVICE_TYPE=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['device_type'])")
BOX_MODEL=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('box_model_name', 'N/A'))")
FBX_UID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['uid'])")

MAJOR_VERSION="${API_VERSION%%.*}"
FBX_BASE="https://${API_DOMAIN}:${HTTPS_PORT}${API_BASE_URL}v${MAJOR_VERSION}"

echo ""
echo "Freebox found:"
echo "  Model:       $BOX_MODEL ($DEVICE_TYPE)"
echo "  API version: $API_VERSION"
echo "  Domain:      $API_DOMAIN"
echo "  HTTPS port:  $HTTPS_PORT"
echo "  UID:         $FBX_UID"
echo "  Base URL:    $FBX_BASE"
echo ""

# Save to OS secret store
secret_set "freebox-api-base" "$FBX_BASE"
echo "Base URL saved to OS secret store (freebox-api-base)"
