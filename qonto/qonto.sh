#!/usr/bin/env bash
# Compatibility dispatcher for the Qonto skill scripts.
# Source this file to load `qonto`, or execute it directly.

QONTO_SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

qonto() {
  local command_name="${1:-help}"
  if [[ $# -gt 0 ]]; then
    shift
  fi

  case "$command_name" in
    help|-h|--help)
      cat <<'USAGE'
qonto — read-only Qonto helper

Usage:
  qonto transactions [options]       List/search all transactions, auto-paginated
  qonto search [options]             Alias for transactions
  qonto get ID [--format FORMAT]     Read one transaction
  qonto organization                 Read organization information
  qonto memberships [key=value ...]  Read memberships
  qonto request ENDPOINT [args...]   Run another read-only GET request
  qonto help                         Show this help

Examples:
  qonto transactions --year 2025 --side debit --status completed --format report
  qonto transactions --days 30 --sort desc --limit 20 --format tsv
  qonto get TRANSACTION_ID --format summary
USAGE
      ;;
    transactions|txns|search)
      command bash "$QONTO_SKILL_DIR/scripts/list-transactions.sh" "$@"
      ;;
    get|transaction)
      command bash "$QONTO_SKILL_DIR/scripts/get-transaction.sh" "$@"
      ;;
    organization|org)
      command bash "$QONTO_SKILL_DIR/scripts/request-template.sh" /organization "$@"
      ;;
    memberships)
      command bash "$QONTO_SKILL_DIR/scripts/request-template.sh" /memberships "$@"
      ;;
    request)
      command bash "$QONTO_SKILL_DIR/scripts/request-template.sh" "$@"
      ;;
    *)
      printf 'ERROR: Unknown qonto command: %s\n' "$command_name" >&2
      printf '%s\n' 'Run qonto help for usage.' >&2
      return 2
      ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  qonto "$@"
fi
