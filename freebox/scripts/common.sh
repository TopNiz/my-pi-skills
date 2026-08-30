#!/usr/bin/env bash
# Skill-local Freebox credential helpers.
# Credentials are stored in ../.env with owner-only permissions so the skill
# works from local and remote shells without an OS-specific keychain.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
FREEBOX_ENV_FILE="$SKILL_DIR/.env"

_secret_env_key() {
  case "$1" in
    freebox-api-base) printf '%s' 'FREEBOX_API_BASE' ;;
    freebox-app-id) printf '%s' 'FREEBOX_APP_ID' ;;
    freebox-app-token) printf '%s' 'FREEBOX_APP_TOKEN' ;;
    freebox-session-token) printf '%s' 'FREEBOX_SESSION_TOKEN' ;;
    *) return 1 ;;
  esac
}

_load_freebox_env() {
  [ -r "$FREEBOX_ENV_FILE" ] || return 1
  # This file is created and maintained by this skill; values are shell-escaped.
  # shellcheck disable=SC1090
  set -a
  . "$FREEBOX_ENV_FILE"
  set +a
}

secret_get() {
  local env_key value
  env_key=$(_secret_env_key "$1") || return 1
  _load_freebox_env || return 1
  value="${!env_key-}"
  [ -n "$value" ] || return 1
  printf '%s' "$value"
}

secret_set() {
  local env_key="$(_secret_env_key "$1")" value="$2" tmp escaped
  [ -n "$env_key" ] || return 1

  umask 077
  tmp=$(mktemp "$FREEBOX_ENV_FILE.XXXXXX")
  if [ -f "$FREEBOX_ENV_FILE" ]; then
    grep -v -F "${env_key}=" "$FREEBOX_ENV_FILE" > "$tmp" || true
  else
    printf '%s\n' '# Freebox API credentials — generated locally; do not commit or share.' > "$tmp"
  fi
  printf -v escaped '%q' "$value"
  printf '%s=%s\n' "$env_key" "$escaped" >> "$tmp"
  chmod 600 "$tmp"
  mv "$tmp" "$FREEBOX_ENV_FILE"
  printf -v "$env_key" '%s' "$value"
  export "$env_key"
}
