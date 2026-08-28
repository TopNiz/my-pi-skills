#!/usr/bin/env bash
# Cross-platform secret storage helpers for Freebox scripts.
# macOS: Keychain via `security`; Windows: DPAPI CurrentUser encryption via winsecret.ps1.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_is_windows() {
  case "$(uname -s 2>/dev/null || true)" in
    MINGW*|MSYS*|CYGWIN*) return 0 ;;
    *) return 1 ;;
  esac
}

secret_get() {
  local key="$1"
  if command -v security >/dev/null 2>&1; then
    security find-generic-password -a "freebox" -s "$key" -w 2>/dev/null || return 1
  elif _is_windows && command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$SCRIPT_DIR/winsecret.ps1" get "$key" 2>/dev/null | tr -d '\r'
  elif command -v pwsh >/dev/null 2>&1; then
    pwsh -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$SCRIPT_DIR/winsecret.ps1" get "$key" 2>/dev/null
  else
    return 1
  fi
}

secret_set() {
  local key="$1"
  local value="$2"
  if command -v security >/dev/null 2>&1; then
    security add-generic-password -a "freebox" -s "$key" -w "$value" -U >/dev/null 2>&1
  elif _is_windows && command -v powershell.exe >/dev/null 2>&1; then
    printf '%s' "$value" | powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$SCRIPT_DIR/winsecret.ps1" set "$key" >/dev/null
  elif command -v pwsh >/dev/null 2>&1; then
    printf '%s' "$value" | pwsh -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$SCRIPT_DIR/winsecret.ps1" set "$key" >/dev/null
  else
    echo "❌ No supported secret store found" >&2
    return 1
  fi
}
