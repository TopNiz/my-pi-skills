#!/usr/bin/env bash
# List Qonto bank transactions across every bank account with automatic pagination.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=qonto-common.sh
source "$SCRIPT_DIR/qonto-common.sh"

usage() {
  cat <<'USAGE'
Usage: list-transactions.sh [options]

Account selection (default: discover and query every Qonto bank account):
  --account-id ID       Query one bank account ID
  --iban IBAN           Query one IBAN

Filters:
  --year YYYY           Calendar year; cannot be combined with --from/--to/--days
  --from YYYY-MM-DD     First settlement date
  --to YYYY-MM-DD       Last settlement date
  --days N              Last N days
  --status STATUS       pending | completed | declined
  --side SIDE           debit | credit
  --min-cents N         Minimum amount in cents (alias: --min)
  --max-cents N         Maximum amount in cents (alias: --max)
  --label TEXT          Case-insensitive label filter (applied locally)

Output:
  --format FORMAT       json | jsonl | tsv | summary | report (default: json)
  --sort ORDER          asc | desc by transaction date (default: asc)
  --limit N             Keep N rows after collecting and sorting; 0 means all
  -h, --help            Show this help

Examples:
  list-transactions.sh --year 2025 --side debit --status completed --format report
  list-transactions.sh --days 30 --sort desc --limit 20 --format tsv
  list-transactions.sh --from 2025-01-01 --to 2025-12-31 --format json
USAGE
}

fail() {
  printf 'ERROR: %s\n' "$1" >&2
  exit 2
}

require_value() {
  local option="$1"
  local remaining="$2"
  [[ "$remaining" -ge 2 ]] || fail "$option requires a value."
}

year=""
from_date=""
to_date=""
days=""
status=""
side=""
min_cents=""
max_cents=""
label=""
account_id=""
iban=""
format="json"
sort_order="asc"
limit="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --year) require_value "$1" "$#"; year="$2"; shift 2 ;;
    --from) require_value "$1" "$#"; from_date="$2"; shift 2 ;;
    --to) require_value "$1" "$#"; to_date="$2"; shift 2 ;;
    --days) require_value "$1" "$#"; days="$2"; shift 2 ;;
    --status) require_value "$1" "$#"; status="$2"; shift 2 ;;
    --side) require_value "$1" "$#"; side="$2"; shift 2 ;;
    --min-cents|--min) require_value "$1" "$#"; min_cents="$2"; shift 2 ;;
    --max-cents|--max) require_value "$1" "$#"; max_cents="$2"; shift 2 ;;
    --label) require_value "$1" "$#"; label="$2"; shift 2 ;;
    --account-id) require_value "$1" "$#"; account_id="$2"; shift 2 ;;
    --iban) require_value "$1" "$#"; iban="$2"; shift 2 ;;
    --format) require_value "$1" "$#"; format="$2"; shift 2 ;;
    --sort) require_value "$1" "$#"; sort_order="$2"; shift 2 ;;
    --limit) require_value "$1" "$#"; limit="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) fail "Unknown option: $1" ;;
  esac
done

[[ -z "$year" || "$year" =~ ^[0-9]{4}$ ]] || fail '--year must be a four-digit year.'
[[ -z "$from_date" || "$from_date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || fail '--from must use YYYY-MM-DD.'
[[ -z "$to_date" || "$to_date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || fail '--to must use YYYY-MM-DD.'
[[ -z "$days" || "$days" =~ ^[1-9][0-9]*$ ]] || fail '--days must be a positive integer.'
[[ -z "$min_cents" || "$min_cents" =~ ^[0-9]+$ ]] || fail '--min-cents must be a non-negative integer.'
[[ -z "$max_cents" || "$max_cents" =~ ^[0-9]+$ ]] || fail '--max-cents must be a non-negative integer.'
[[ "$limit" =~ ^[0-9]+$ ]] || fail '--limit must be a non-negative integer.'
[[ -z "$status" || "$status" =~ ^(pending|completed|declined)$ ]] || fail 'Invalid --status value.'
[[ -z "$side" || "$side" =~ ^(debit|credit)$ ]] || fail 'Invalid --side value.'
[[ "$format" =~ ^(json|jsonl|tsv|summary|report)$ ]] || fail 'Invalid --format value.'
[[ "$sort_order" =~ ^(asc|desc)$ ]] || fail '--sort must be asc or desc.'
[[ -z "$account_id" || -z "$iban" ]] || fail 'Use either --account-id or --iban, not both.'

if [[ -n "$year" && ( -n "$from_date" || -n "$to_date" || -n "$days" ) ]]; then
  fail '--year cannot be combined with --from, --to, or --days.'
fi
if [[ -n "$days" && ( -n "$from_date" || -n "$to_date" ) ]]; then
  fail '--days cannot be combined with --from or --to.'
fi

if [[ -n "$year" ]]; then
  from_date="${year}-01-01"
  to_date="${year}-12-31"
elif [[ -n "$days" ]]; then
  to_date="$(date +%Y-%m-%d)"
  if date -v-"${days}"d +%Y-%m-%d >/dev/null 2>&1; then
    from_date="$(date -v-"${days}"d +%Y-%m-%d)"
  elif date -d "${days} days ago" +%Y-%m-%d >/dev/null 2>&1; then
    from_date="$(date -d "${days} days ago" +%Y-%m-%d)"
  else
    fail 'Could not calculate --days with the installed date command.'
  fi
fi

selectors=()
selector_count=0
if [[ -n "$account_id" ]]; then
  selectors+=("bank_account_id=$account_id")
  selector_count=$((selector_count + 1))
elif [[ -n "$iban" ]]; then
  selectors+=("iban=$iban")
  selector_count=$((selector_count + 1))
else
  organization_json="$(qonto_api_get '/organization')"
  selector_lines="$(jq -r '
    .organization.bank_accounts[]?
    | if ((.id // "") | length) > 0 then
        "bank_account_id=" + .id
      elif ((.iban // "") | length) > 0 then
        "iban=" + .iban
      else
        empty
      end
  ' <<<"$organization_json")"

  while IFS= read -r selector; do
    if [[ -n "$selector" ]]; then
      selectors+=("$selector")
      selector_count=$((selector_count + 1))
    fi
  done <<<"$selector_lines"
fi

[[ "$selector_count" -gt 0 ]] || fail 'No Qonto bank accounts were found.'

emit_transactions() {
  local selector page next_page body
  local -a query

  for selector in "${selectors[@]}"; do
    page=1
    while :; do
      query=("$selector" "per_page=100" "current_page=$page")
      [[ -n "$status" ]] && query+=("status=$status")
      [[ -n "$side" ]] && query+=("side=$side")
      [[ -n "$min_cents" ]] && query+=("min_amount=$min_cents")
      [[ -n "$max_cents" ]] && query+=("max_amount=$max_cents")
      [[ -n "$from_date" ]] && query+=("settled_at_from=$from_date")
      [[ -n "$to_date" ]] && query+=("settled_at_to=$to_date")

      body="$(qonto_api_get '/transactions' "${query[@]}")"
      if ! jq -e '.transactions | type == "array"' >/dev/null 2>&1 <<<"$body"; then
        printf '%s\n' 'ERROR: Qonto returned an unexpected transactions response.' >&2
        return 1
      fi

      jq -c '.transactions[]?' <<<"$body"
      next_page="$(jq -r '.meta.next_page // empty' <<<"$body")"
      [[ -n "$next_page" ]] || break
      [[ "$next_page" != "$page" ]] || {
        printf '%s\n' 'ERROR: Qonto pagination did not advance.' >&2
        return 1
      }
      page="$next_page"
      [[ "$page" -le 10000 ]] || {
        printf '%s\n' 'ERROR: Qonto pagination exceeded the safety limit.' >&2
        return 1
      }
    done
  done
}

transactions_json="$(emit_transactions | jq -s \
  --arg label_lc "$(printf '%s' "$label" | tr '[:upper:]' '[:lower:]')" \
  --arg sort_order "$sort_order" \
  --argjson limit "$limit" '
    (if $label_lc == "" then . else
      map(select((.label // "" | ascii_downcase) | contains($label_lc)))
    end)
    | sort_by(.settled_at // .emitted_at // .updated_at // "", .id // "")
    | if $sort_order == "desc" then reverse else . end
    | if $limit > 0 then .[0:$limit] else . end
  ')"

case "$format" in
  json)
    jq '.' <<<"$transactions_json"
    ;;
  jsonl)
    jq -c '.[]' <<<"$transactions_json"
    ;;
  tsv)
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
      (["date", "amount", "currency", "side", "status", "label", "reference", "id"] | @tsv),
      (.[] | [
        ((.settled_at // .emitted_at // "")[0:10]),
        ((.amount_cents // 0) | money),
        (.currency // .amount_currency // ""),
        (.side // ""),
        (.status // ""),
        (.label // ""),
        (.reference // ""),
        (.id // "")
      ] | @tsv)
    ' <<<"$transactions_json"
    ;;
  summary)
    jq '
      def currency: (.currency // .amount_currency // "UNKNOWN");
      def absolute_cents: (.amount_cents // 0) | if . < 0 then -. else . end;
      {
        count: length,
        totals_by_currency: (
          sort_by(currency)
          | group_by(currency)
          | map({
              currency: (.[0] | currency),
              transaction_count: length,
              debit_cents: ([.[] | select(.side == "debit") | absolute_cents] | add // 0),
              credit_cents: ([.[] | select(.side == "credit") | absolute_cents] | add // 0),
              net_cents: ([.[].amount_cents // 0] | add // 0)
            })
        ),
        monthly: (
          sort_by([((.settled_at // .emitted_at // "")[0:7]), currency])
          | group_by([((.settled_at // .emitted_at // "")[0:7]), currency])
          | map({
              month: ((.[0].settled_at // .[0].emitted_at // "")[0:7]),
              currency: (.[0] | currency),
              transaction_count: length,
              debit_cents: ([.[] | select(.side == "debit") | absolute_cents] | add // 0),
              credit_cents: ([.[] | select(.side == "credit") | absolute_cents] | add // 0),
              net_cents: ([.[].amount_cents // 0] | add // 0)
            })
        )
      }
    ' <<<"$transactions_json"
    ;;
  report)
    jq -r '
      def currency: (.currency // .amount_currency // "UNKNOWN");
      def absolute_cents: (.amount_cents // 0) | if . < 0 then -. else . end;
      def money:
        if . == null then "" else
          . as $v
          | (if $v < 0 then -$v else $v end) as $a
          | (if $v < 0 then "-" else "" end)
            + (((($a / 100) | floor)) | tostring)
            + "."
            + (($a % 100) | tostring | if length == 1 then "0" + . else . end)
        end;
      . as $transactions
      | "Transactions: \(length)",
        "Totals:",
        ($transactions
          | sort_by(currency)
          | group_by(currency)[]
          | (.[0] | currency) as $currency
          | ([.[] | select(.side == "debit") | absolute_cents] | add // 0) as $debits
          | ([.[] | select(.side == "credit") | absolute_cents] | add // 0) as $credits
          | ([.[].amount_cents // 0] | add // 0) as $net
          | "  \($currency): debits \($debits | money), credits \($credits | money), net \($net | money)"
        ),
        "",
        (["date", "amount", "currency", "side", "status", "label", "reference", "id"] | @tsv),
        ($transactions[] | [
          ((.settled_at // .emitted_at // "")[0:10]),
          ((.amount_cents // 0) | money),
          currency,
          (.side // ""),
          (.status // ""),
          (.label // ""),
          (.reference // ""),
          (.id // "")
        ] | @tsv)
    ' <<<"$transactions_json"
    ;;
esac
