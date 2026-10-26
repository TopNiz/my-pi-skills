#!/usr/bin/env bash
# Generic authenticated Rocket.Chat REST caller.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=rc-common.sh
. "$SCRIPT_DIR/rc-common.sh"

usage() {
  cat <<'EOF'
Usage:
  rc.sh METHOD /api/path [options]

Options:
  --json '<json>'   JSON request body (POST/PUT)
  --data k=v        Query parameter (GET) or form field (POST). Repeatable.
  --data=k=v        Same as --data k=v
  -h, --help        Show this help

Examples:
  rc.sh GET  /api/v1/me
  rc.sh GET  /api/v1/users.info username=nizarayed
  rc.sh GET  /api/v1/users.list count=50 offset=0
  rc.sh GET  /api/v1/channels.list count=100
  rc.sh POST /api/v1/channels.create --json '{"name":"ops","members":["nizarayed"]}'
  rc.sh POST /api/v1/channels.archive --json '{"roomName":"ops"}'
  rc.sh POST /api/v1/users.setActiveStatus --json '{"userId":"abc","activeStatus":false}'

Hard deletes (DELETE or *.delete) are refused unless RC_ALLOW_HARD_DELETE=1.
EOF
}

if [[ $# -lt 2 ]]; then
  usage
  exit 2
fi

method="$(printf '%s' "$1" | tr '[:lower:]' '[:upper:]')"
path="$2"
shift 2

if [[ "$path" != /api/* ]]; then
  printf 'ERROR: Path must start with /api/: %s\n' "$path" >&2
  exit 2
fi

json_body=""
declare -a data_args=()

while (($#)); do
  case "$1" in
    --json)
      json_body="${2:-}"
      shift 2
      ;;
    --json=*)
      json_body="${1#*=}"
      shift
      ;;
    --data)
      data_args+=("${2:-}")
      shift 2
      ;;
    --data=*)
      data_args+=("${1#*=}")
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *=*)
      data_args+=("$1")
      shift
      ;;
    *)
      printf 'ERROR: Unknown argument: %s\n' "$1" >&2
      exit 2
      ;;
  esac
done

rc_load_env || exit 1

if rc_hard_delete_blocked "$method" "$path"; then
  rc_hard_delete_message "$path"
  exit 1
fi

url="${RC_URL%/}${path}"
declare -a curl_args=(
  --silent
  --show-error
  --connect-timeout 10
  --max-time 120
  --header "Accept: application/json"
  --header "X-User-Id: ${RC_USER_ID}"
  --header "X-Auth-Token: ${RC_AUTH_TOKEN}"
  --write-out $'\n%{http_code}'
)

if [[ "$method" == "GET" || "$method" == "HEAD" ]]; then
  curl_args+=(--get)
  local_param=""
  for local_param in "${data_args[@]:-}"; do
    [[ -z "$local_param" ]] && continue
    curl_args+=(--data-urlencode "$local_param")
  done
else
  curl_args+=(--request "$method")
  if [[ -n "$json_body" ]]; then
    curl_args+=(--header "Content-Type: application/json" --data "$json_body")
  else
    for local_param in "${data_args[@]:-}"; do
      [[ -z "$local_param" ]] && continue
      curl_args+=(--data-urlencode "$local_param")
    done
  fi
fi

response="$(curl "${curl_args[@]}" "$url")" || {
  printf 'ERROR: Network request failed: %s\n' "$url" >&2
  exit 1
}

http_status="${response##*$'\n'}"
body="${response%$'\n'*}"

if [[ -n "$body" ]]; then
  printf '%s\n' "$body" | rc_pretty
fi

if [[ "$http_status" -ge 400 ]]; then
  printf 'HTTP %s\n' "$http_status" >&2
  exit 1
fi
