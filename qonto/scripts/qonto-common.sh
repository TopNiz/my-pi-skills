#!/usr/bin/env bash
# Shared, read-only Qonto API helpers. Source this file; do not execute it.

QONTO_API_BASE_URL="https://thirdparty.qonto.com/v2"
_QONTO_SIGNIN=""
_QONTO_SECRET=""

qonto_require_runtime() {
  local command_name
  for command_name in security curl jq; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
      printf 'ERROR: Required command not found: %s\n' "$command_name" >&2
      return 1
    fi
  done
}

qonto_load_credentials() {
  local keychain_account

  if [[ -n "$_QONTO_SIGNIN" && -n "$_QONTO_SECRET" ]]; then
    return 0
  fi

  qonto_require_runtime || return 1
  keychain_account="${USER:-$(id -un)}"

  if ! _QONTO_SIGNIN="$(security find-generic-password -a "$keychain_account" -s "qonto-signin" -w 2>/dev/null)" \
    || [[ -z "$_QONTO_SIGNIN" ]]; then
    printf 'ERROR: Qonto sign-in is missing from the macOS keychain.\n' >&2
    return 1
  fi

  if ! _QONTO_SECRET="$(security find-generic-password -a "$keychain_account" -s "qonto-secret-key" -w 2>/dev/null)" \
    || [[ -z "$_QONTO_SECRET" ]]; then
    printf 'ERROR: Qonto secret key is missing from the macOS keychain.\n' >&2
    return 1
  fi
}

qonto_print_api_error() {
  local http_status="$1"
  local endpoint="$2"
  local body="$3"
  local detail=""

  case "$http_status" in
    401)
      printf '%s\n' 'ERROR: Authentication failed — the Qonto API key may be expired or invalid.' >&2
      ;;
    403)
      printf 'ERROR: Qonto denied access to %s (HTTP 403).\n' "$endpoint" >&2
      ;;
    *)
      printf 'ERROR: Qonto request to %s failed (HTTP %s).\n' "$endpoint" "$http_status" >&2
      ;;
  esac

  detail="$(jq -r '
    [
      (.message? | strings),
      (.error? | strings),
      (.errors[]? | (.detail? // .message? // .code? // empty) | strings)
    ]
    | map(select(length > 0))
    | unique
    | .[:3]
    | join("; ")
  ' <<<"$body" 2>/dev/null || true)"

  if [[ -n "$detail" ]]; then
    printf 'Qonto response: %s\n' "$detail" >&2
  fi
}

# Perform a read-only GET against the fixed Qonto API host.
# Usage: qonto_api_get /endpoint "key=value" "other=value"
qonto_api_get() {
  local endpoint="${1:-}"
  shift || true

  if [[ -z "$endpoint" || "$endpoint" != /* || "$endpoint" == *://* \
    || "$endpoint" == *'..'* || "$endpoint" == *'?'* ]]; then
    printf '%s\n' 'ERROR: Endpoint must be a relative Qonto API path without a query string.' >&2
    return 1
  fi

  qonto_load_credentials || return 1

  local parameter
  local -a curl_args
  curl_args=(
    --silent
    --show-error
    --get
    --connect-timeout 10
    --max-time 60
    --retry 2
    --retry-delay 1
    --header "Accept: application/json"
    --header "Authorization: ${_QONTO_SIGNIN}:${_QONTO_SECRET}"
    --write-out $'\n%{http_code}'
  )

  for parameter in "$@"; do
    if [[ "$parameter" != *=* ]]; then
      printf 'ERROR: Query parameter must use key=value syntax: %s\n' "$parameter" >&2
      return 1
    fi
    curl_args+=(--data-urlencode "$parameter")
  done

  local response http_status body
  if ! response="$(curl "${curl_args[@]}" "${QONTO_API_BASE_URL}${endpoint}")"; then
    printf 'ERROR: Network request to Qonto failed for %s.\n' "$endpoint" >&2
    return 1
  fi

  if [[ "$response" != *$'\n'* ]]; then
    printf 'ERROR: Qonto returned an unexpected response for %s.\n' "$endpoint" >&2
    return 1
  fi

  http_status="${response##*$'\n'}"
  body="${response%$'\n'*}"

  case "$http_status" in
    2??)
      printf '%s\n' "$body"
      ;;
    *)
      qonto_print_api_error "$http_status" "$endpoint" "$body"
      return 1
      ;;
  esac
}
