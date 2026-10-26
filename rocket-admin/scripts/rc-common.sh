#!/usr/bin/env bash
# Shared helpers for the rocket-admin skill. Source this file; do not execute it.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RC_ENV_FILE="$SKILL_DIR/.env"
RC_DEFAULT_URL="https://rocket.codimeo.com"

rc_require_runtime() {
  local command_name
  for command_name in curl; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
      printf 'ERROR: Required command not found: %s\n' "$command_name" >&2
      return 1
    fi
  done
}

rc_require_jq() {
  if ! command -v jq >/dev/null 2>&1; then
    printf 'ERROR: jq is required for this operation.\n' >&2
    return 1
  fi
}

# Load RC_URL without requiring credentials. Useful for spec/index commands.
rc_optional_env() {
  if [[ -r "$RC_ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    . "$RC_ENV_FILE"
    set +a
  fi
  : "${RC_URL:=$RC_DEFAULT_URL}"
}

# Load the full bot credential set.
rc_load_env() {
  rc_require_runtime || return 1
  rc_optional_env
  if [[ -z "${RC_USER_ID:-}" || -z "${RC_AUTH_TOKEN:-}" ]]; then
    printf 'ERROR: Missing RC_USER_ID or RC_AUTH_TOKEN.\n' >&2
    printf 'Run scripts/setup-bot.sh once, or fill %s.\n' "$RC_ENV_FILE" >&2
    return 1
  fi
}

rc_pretty() {
  if command -v jq >/dev/null 2>&1; then
    jq . 2>/dev/null || cat
  elif command -v python3 >/dev/null 2>&1; then
    python3 -m json.tool 2>/dev/null || cat
  else
    cat
  fi
}

# Fetch the live OpenAPI spec into a cache file and print its path.
# Usage: rc_fetch_spec doc|full
rc_fetch_spec() {
  local mode="${1:-doc}"
  local name url
  rc_optional_env
  case "$mode" in
    full) name="openapi-undocumented.json"; url="${RC_URL%/}/api/docs/json?withUndocumented=true" ;;
    doc)  name="openapi.json";              url="${RC_URL%/}/api/docs/json" ;;
    *) printf 'ERROR: rc_fetch_spec expects doc or full, got: %s\n' "$mode" >&2; return 2 ;;
  esac

  local cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/rocket-admin"
  mkdir -p "$cache_dir"
  local out="$cache_dir/$name"
  local tmp="$out.tmp.$$"

  if curl -fsS --connect-timeout 10 --max-time 60 "$url" -o "$tmp"; then
    mv "$tmp" "$out"
  else
    rm -f "$tmp"
    if [[ ! -s "$out" ]]; then
      printf 'ERROR: Could not fetch the live spec from %s\n' "$url" >&2
      return 1
    fi
    printf 'WARN: Live spec fetch failed; using cached copy %s\n' "$out" >&2
  fi

  printf '%s\n' "$out"
}

# Hard deletes are blocked unless RC_ALLOW_HARD_DELETE=1.
rc_hard_delete_blocked() {
  local method="$1"
  local path="$2"
  [[ "${RC_ALLOW_HARD_DELETE:-0}" == "1" ]] && return 1
  [[ "$method" == "DELETE" ]] && return 0
  [[ "$path" =~ \.delete$ ]] && return 0
  [[ "$path" =~ /delete$ ]] && return 0
  [[ "$path" == "/api/v1/integrations.remove" ]] && return 0
  return 1
}

rc_hard_delete_message() {
  local path="$1"
  cat >&2 <<EOF
ERROR: Hard delete is disabled for: $path

This skill uses logical deletion so that a human can purge later:
  users     -> POST /api/v1/users.setActiveStatus  {"userId":"...","activeStatus":false}
  channels  -> POST /api/v1/channels.archive
  groups    -> POST /api/v1/groups.archive
  rooms     -> POST /api/v1/rooms.changeArchivationState  {"rid":"...","action":"archive"}
  teams     -> archive the team's rooms; teams.delete is permanent

If you really need a permanent delete, run the command with:
  RC_ALLOW_HARD_DELETE=1 bash scripts/rc.sh ...
EOF
}
