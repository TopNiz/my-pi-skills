#!/usr/bin/env bash
# Fetch one Qonto transaction by ID.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=qonto-common.sh
source "$SCRIPT_DIR/qonto-common.sh"

usage() {
  cat <<'USAGE'
Usage: get-transaction.sh TRANSACTION_ID [--format json|summary]

Formats:
  json       Complete transaction object (default)
  summary    Compact human-readable fields
USAGE
}

[[ $# -gt 0 ]] || { usage >&2; exit 2; }
case "${1:-}" in
  -h|--help) usage; exit 0 ;;
esac

transaction_id="$1"
shift
format="json"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --format)
      [[ $# -ge 2 ]] || { printf '%s\n' 'ERROR: --format requires a value.' >&2; exit 2; }
      format="$2"
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'ERROR: Unknown option: %s\n' "$1" >&2; exit 2 ;;
  esac
done

[[ "$transaction_id" =~ ^[A-Za-z0-9_-]+$ ]] || {
  printf '%s\n' 'ERROR: Invalid transaction ID.' >&2
  exit 2
}
[[ "$format" =~ ^(json|summary)$ ]] || {
  printf '%s\n' 'ERROR: --format must be json or summary.' >&2
  exit 2
}

response_json="$(qonto_api_get "/transactions/$transaction_id")"
transaction_json="$(jq '(.transaction // .)' <<<"$response_json")"

if ! jq -e 'type == "object" and (.id? != null)' >/dev/null 2>&1 <<<"$transaction_json"; then
  printf '%s\n' 'ERROR: Qonto returned an unexpected transaction response.' >&2
  exit 1
fi

case "$format" in
  json)
    jq '.' <<<"$transaction_json"
    ;;
  summary)
    jq -r '
      def money:
        if . == null then "" else
          . as $v
          | (if $v < 0 then -$v else $v end) as $a
          | (if $v < 0 then "-" else "" end)
            + (((($a / 100) | floor)) | tostring)
            + "."
            + (($a % 100) | tostring | if length == 1 then "0" + . else . end)
        end;
      "ID: \(.id // "")",
      "Date: \((.settled_at // .emitted_at // ""))",
      "Label: \(.label // "")",
      "Reference: \(.reference // "")",
      "Amount: \((.amount_cents // 0) | money) \(.currency // .amount_currency // "")",
      "Side: \(.side // "")",
      "Status: \(.status // "")",
      "VAT: \(if .vat_amount_cents == null then "not provided" else ((.vat_amount_cents | money) + " " + (.currency // .amount_currency // "")) end)",
      "Category ID: \(.cash_flow_category_id // "")",
      "Attachments: \((.attachment_ids // []) | length)"
    ' <<<"$transaction_json"
    ;;
esac
