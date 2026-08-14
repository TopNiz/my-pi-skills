#!/usr/bin/env bash
# Generic template for read-only Qonto GET requests.
# Adapt the endpoint and key=value query arguments; authentication and HTTP
# handling should remain in qonto-common.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=qonto-common.sh
source "$SCRIPT_DIR/qonto-common.sh"

usage() {
  cat <<'USAGE'
Usage: request-template.sh ENDPOINT [key=value ...] [--format pretty|compact|raw]

ENDPOINT must be relative to https://thirdparty.qonto.com/v2 and must not
contain a query string. Pass each query parameter as a separate key=value arg.
Only read-only GET requests are supported.

Examples:
  request-template.sh /organization
  request-template.sh /memberships per_page=100 current_page=1
  request-template.sh /labels per_page=100 --format compact

Adaptation pattern:
  endpoint="/your-endpoint"
  query=("first=value" "second=value")
  qonto_api_get "$endpoint" "${query[@]}" | jq .
USAGE
}

[[ $# -gt 0 ]] || { usage >&2; exit 2; }
case "${1:-}" in
  -h|--help) usage; exit 0 ;;
esac

endpoint="$1"
shift
format="pretty"
query=()
query_count=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --format)
      [[ $# -ge 2 ]] || { printf '%s\n' 'ERROR: --format requires a value.' >&2; exit 2; }
      format="$2"
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *=*) query+=("$1"); query_count=$((query_count + 1)); shift ;;
    *) printf 'ERROR: Expected key=value or an option, got: %s\n' "$1" >&2; exit 2 ;;
  esac
done

[[ "$format" =~ ^(pretty|compact|raw)$ ]] || {
  printf '%s\n' 'ERROR: --format must be pretty, compact, or raw.' >&2
  exit 2
}

if [[ "$query_count" -gt 0 ]]; then
  response_json="$(qonto_api_get "$endpoint" "${query[@]}")"
else
  response_json="$(qonto_api_get "$endpoint")"
fi
case "$format" in
  pretty) jq '.' <<<"$response_json" ;;
  compact) jq -c '.' <<<"$response_json" ;;
  raw) printf '%s\n' "$response_json" ;;
esac
