---
name: coinbase
description: Securely review Coinbase balances, portfolios, and bounded order history through a VPN/IP-allowlisted View-only API adapter. Use for general Coinbase account reviews, portfolio analysis, order-history summaries, API-access checks, and educational investment-strategy discussions. Trading and transfers are not implemented in the current adapter.
---

# Coinbase

This is a global Coinbase skill. Its current implementation is a View-only adapter backed by the local XRP Strategy project; that project is an implementation detail, not a restriction on which Coinbase assets or portfolios can be reviewed.

```sh
REPO="/Users/nizarayed/MyDocuments/002-git/xrp-strategy"
SKILL_DIR="/Users/nizarayed/.agents/skills/coinbase"
RUNNER="$SKILL_DIR/scripts/coinbase_readonly.py"
```

The credential configuration is stored at `$SKILL_DIR/.env`, outside the Git project. It must never be printed, copied, inspected, or committed.

## Current capability and boundaries

- The implemented adapter is **View-only**: accounts, portfolios, portfolio breakdowns, and bounded order history.
- It has no command for orders, transfers, withdrawals, deposits, API-key management, or account/security changes.
- Never place, preview, edit, or cancel an order; transfer assets; or change account settings through this skill.
- Never display, inspect, copy, or modify API credentials, cookies, browser storage, tokens, or `.env` contents. Do not run shell tracing, debug logging, or environment dumps.
- Do not create, revoke, rotate, or alter Coinbase API keys. The user manages keys directly in Coinbase.
- Future trading functionality is out of scope until the user explicitly requests a separately designed and reviewed implementation. Any future financial action must require a clear, per-action user confirmation immediately before execution.

## VPN/IP allowlist requirement

Coinbase API access requires the VPN egress address to match the key’s Coinbase IP whitelist. The global `.env` includes a non-secret allowlist setting:

```dotenv
COINBASE_ALLOWED_IP=VPN_EGRESS_IPV4_OR_CIDR
```

The runner loads this configuration without printing it, checks the active public IPv4 address, and **refuses to call Coinbase unless the active address belongs to the configured IPv4 address/CIDR**. A `/32` CIDR represents one specific IP address.

- Do not connect, disconnect, or reconfigure the VPN unless the user explicitly asks.
- If the check fails, ask the user to connect to the correct VPN or correct the local allowlist configuration. Do not disclose either address.
- Never bypass or disable the allowlist check.

## Safe View-only commands

All Coinbase requests must go through the wrapper.

```sh
# Available and held balance by currency
"$REPO/.venv/bin/python" "$RUNNER" account

# Accessible portfolios; do not expose IDs unless selecting a portfolio
"$REPO/.venv/bin/python" "$RUNNER" portfolios

# Overall and crypto portfolio balance breakdown
"$REPO/.venv/bin/python" "$RUNNER" portfolio --id PORTFOLIO_ID

# Latest bounded order page (maximum 100 results)
"$REPO/.venv/bin/python" "$RUNNER" orders --limit 100

# Bounded order history for any Coinbase product and status
"$REPO/.venv/bin/python" "$RUNNER" orders --product-id PRODUCT-ID --status FILLED --limit 100
```

Interpretation:

- Account table returned: VPN allowlist and View-only API access work.
- VPN/IP error: connect to the required VPN or correct `COINBASE_ALLOWED_IP` locally; do not bypass the check.
- `401 Unauthorized`: the View-only credentials are invalid, expired, revoked, mismatched, or lack the required permission. Ask the user to update them locally; never request their values.
- Other request error: report only the high-level failure and ask whether to retry later.

`orders` is a single bounded page of up to 100 orders. It may not be complete all-time history and does not include every transfer, reward, conversion, or on-chain transaction.

## Reporting and strategy discussions

For an account review, report total and per-asset available/held balances, concentration, pending/open orders shown, recent filled orders, and the order-history coverage limitation. Do not expose account or portfolio IDs unless the user specifically needs to select one.

For an investment discussion, first establish the user’s time horizon, objective, risk tolerance, liquidity needs, tax jurisdiction, and whether Coinbase is their whole investable portfolio. Offer only general educational, risk-controlled guidance: emergency reserves outside crypto, total and single-asset allocation caps, diversification, recurring contributions only when volatility is acceptable, rebalancing rules, and fees/taxes/custody risk. This is not personalized financial, legal, or tax advice.

Data collection, simulated backtests, and paper-trading runs can write local files. Do not run them without explicit user consent.
