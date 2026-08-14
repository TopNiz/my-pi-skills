---
name: qonto
description: Read Qonto account information and efficiently list, search, summarize, and inspect bank transactions with automatic account discovery and pagination.
allowed-tools: Bash(bash:*) Bash(curl:*) Bash(security:*) Bash(jq:*)
---

# Qonto — read-only account and transaction access

Use the defined scripts in this skill directory for Qonto work. They authenticate from the macOS keychain, keep credentials silent, handle HTTP errors, and target only Qonto's fixed production API host.

## Mandatory fast path

For normal requests, **execute the scripts instead of rebuilding curl calls**:

1. List, filter, summarize, or search transactions with `scripts/list-transactions.sh`.
2. Read one transaction with `scripts/get-transaction.sh`.
3. Use `scripts/request-template.sh` only for another read-only Qonto endpoint.
4. Use `qonto.sh` only as a convenience dispatcher for those scripts.
5. Do not make the same list request twice. `--format report` returns both totals and transaction rows in one API pass.

All paths below are relative to this skill directory (the directory containing `SKILL.md`).

## Defined scripts

### 1. List and search transactions

```bash
bash scripts/list-transactions.sh [options]
```

The script:

- loads keychain credentials once per invocation;
- discovers all Qonto bank account IDs with one organization request unless `--account-id` or `--iban` is supplied;
- includes the required `bank_account_id`/`iban` parameter automatically;
- follows every `meta.next_page` automatically;
- combines and sorts transactions from all accounts;
- URL-encodes every query value;
- can return raw data, a concise list, totals, or a combined report.

Key options:

| Option | Meaning |
|---|---|
| `--year YYYY` | Full calendar year |
| `--from YYYY-MM-DD` / `--to YYYY-MM-DD` | Settlement date range |
| `--days N` | Last N days |
| `--side debit\|credit` | Outgoing or incoming transactions |
| `--status pending\|completed\|declined` | Transaction status |
| `--label TEXT` | Case-insensitive local label search |
| `--min-cents N` / `--max-cents N` | Amount bounds in cents |
| `--sort asc\|desc` | Date order |
| `--limit N` | Keep N rows after sorting; `0` means all |
| `--format json\|jsonl\|tsv\|summary\|report` | Output shape |

Use `json` when more `jq` processing is needed, `tsv` for a compact list with transaction IDs, `summary` for aggregates only, and `report` when the user wants both aggregates and rows.

#### Standard recipes

Completed 2025 debits/expenses, one request flow with totals and rows:

```bash
bash scripts/list-transactions.sh \
  --year 2025 \
  --side debit \
  --status completed \
  --format report
```

Recent transactions:

```bash
bash scripts/list-transactions.sh \
  --days 30 \
  --sort desc \
  --limit 20 \
  --format tsv
```

Search a merchant label:

```bash
bash scripts/list-transactions.sh \
  --from 2025-01-01 \
  --to 2025-12-31 \
  --label 'OPENAI' \
  --format tsv
```

Structured totals:

```bash
bash scripts/list-transactions.sh \
  --year 2025 \
  --side debit \
  --status completed \
  --format summary
```

### 2. Read transaction details

Use the ID returned by the list script:

```bash
bash scripts/get-transaction.sh TRANSACTION_ID
bash scripts/get-transaction.sh TRANSACTION_ID --format summary
```

- `json` (default) returns the complete normalized transaction object.
- `summary` returns selected human-readable fields without account identifiers.
- This is one Qonto request; do not list transactions again when the ID is already known.

### 3. Template for another read-only request

```bash
bash scripts/request-template.sh ENDPOINT [key=value ...]
```

Examples:

```bash
bash scripts/request-template.sh /organization
bash scripts/request-template.sh /memberships per_page=100 current_page=1
bash scripts/request-template.sh /labels per_page=100 --format compact
```

The endpoint must be relative to `https://thirdparty.qonto.com/v2`. Query parameters are separate `key=value` arguments. The template only permits GET requests and never accepts another API host, which prevents credentials from being sent elsewhere.

When adapting the template, change only the endpoint, query parameters, and final `jq` projection. Keep authentication and request handling in `scripts/qonto-common.sh`.

### 4. Convenience dispatcher

```bash
bash qonto.sh transactions --year 2025 --side debit --status completed --format report
bash qonto.sh get TRANSACTION_ID --format summary
bash qonto.sh organization
bash qonto.sh request /memberships per_page=100
```

It can also be sourced:

```bash
source qonto.sh
qonto transactions --days 30 --format tsv
```

## Why direct curl was slow and fragile

The Qonto transactions endpoint requires a `bank_account_id` or `iban`. Older examples that omit it return HTTP 422. A complete manual query therefore needs:

1. a keychain lookup;
2. an organization request to discover accounts;
3. one or more transaction requests for every account;
4. pagination handling;
5. aggregation and formatting.

Ad hoc calls also tend to repeat the entire query once for a summary and again for details. The list script performs account discovery once, loads credentials once, paginates automatically, and can emit summary plus rows in the same invocation.

## Authentication setup

Credentials must exist under these macOS keychain services:

- `qonto-signin`
- `qonto-secret-key`

Verify existence without displaying values:

```bash
security find-generic-password -a "$USER" -s "qonto-signin" -w >/dev/null 2>&1 \
  && printf '%s\n' 'Qonto sign-in found' \
  || printf '%s\n' 'Qonto sign-in missing'

security find-generic-password -a "$USER" -s "qonto-secret-key" -w >/dev/null 2>&1 \
  && printf '%s\n' 'Qonto secret key found' \
  || printf '%s\n' 'Qonto secret key missing'
```

If either entry is missing, the user must generate credentials in Qonto under **Settings → Integrations and Partnerships → API key** and store them directly in the keychain. Never ask the user to paste either value into chat.

## Transaction conventions

- `amount_cents` uses the smallest currency unit.
- Debits are generally negative; reports display signed transaction amounts and separate positive debit/credit aggregates.
- `currency` falls back to `amount_currency` when needed.
- Date filtering uses `settled_at_from` and `settled_at_to`.
- “Expenses” normally means `--side debit --status completed`, but this includes transfers, taxes, and other completed outflows. State this interpretation unless the user requests accounting-only expenses.
- The `tsv` and `report` formats include transaction IDs so a detail request can follow without another search.

## Error handling

- Missing keychain entry: report which entry is missing, never its value.
- HTTP 401: report that authentication failed and the API key may need regeneration.
- HTTP 422: show Qonto's safe validation detail; normally the scripts prevent the missing-account error.
- Network errors: report failure without printing credentials or request headers.
- Never use verbose curl, shell tracing, or commands that print authentication variables.

## Security rules — non-negotiable

1. Never display the Qonto sign-in or secret key, even masked or truncated.
2. Never call the credential-loading helper directly for output.
3. Never use `set -x`, `set -v`, verbose curl, or debug modes around these scripts.
4. Never pass Qonto credentials as script arguments.
5. Never change `QONTO_API_BASE_URL` away from Qonto's fixed production host.
6. Keep this skill read-only; do not add POST, PATCH, PUT, or DELETE operations without a separate explicit user request and safety review.

## References

- [Qonto authentication](https://docs.qonto.com/api-reference/business-api/authentication)
- [Qonto transactions](https://docs.qonto.com/api-reference/business-api/transactions-statements/transactions)
- [Qonto organizations](https://docs.qonto.com/api-reference/business-api/accounts-organizations/organizations)
