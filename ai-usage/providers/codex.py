#!/usr/bin/env python3
"""
Codex (ChatGPT product) Usage & Rate Card Checker

Shows Codex usage status from the ChatGPT backend API (/backend-api/codex/usage),
plus an estimated credit consumption from local Codex CLI history (state_5.sqlite)
computed with the official token-based rate card (help.openai.com/en/articles/20001106).

The token-based rate card (credits per 1M tokens) is current as of 2026-08-07.

Usage:
  ./codex.py                  # Pretty output
  ./codex.py --json           # Raw JSON
  ./codex.py --verbose        # Pretty + raw JSON
"""

import json
import os
import sqlite3
import sys
import urllib.request
from datetime import datetime, timezone

CODEX_AUTH = os.path.expanduser("~/.codex/auth.json")
CODEX_DB = os.path.expanduser("~/.codex/state_5.sqlite")
USAGE_URL = "https://chatgpt.com/backend-api/codex/usage"

# ─────────────────────────────────────────────────────────────
# Official token-based rate card — credits per 1M tokens
# Source: https://help.openai.com/en/articles/20001106-codex-rate-card
# (fetched 2026-08-07). Cache writes are not charged.
# ─────────────────────────────────────────────────────────────
RATE_CARD = {
    "gpt-5.6-sol":        {"input": 125.0,  "cached": 12.50, "output": 750.0},
    "gpt-5.6-terra":      {"input": 50.0,   "cached": 5.0,   "output": 300.0},
    "gpt-5.6-luna":       {"input": 5.0,    "cached": 0.5,   "output": 30.0},
    "gpt-5.5":            {"input": 125.0,  "cached": 12.50, "output": 750.0},
    "gpt-5.5-cyber":      {"input": 312.5,  "cached": 31.25, "output": 1875.0},
    "gpt-5.4":            {"input": 62.5,   "cached": 6.25,  "output": 375.0},
    "gpt-5.4-mini":       {"input": 18.75,  "cached": 1.875, "output": 113.0},
    "gpt-5.3-codex":      {"input": 43.75,  "cached": 4.375, "output": 350.0},
    "gpt-5.2":            {"input": 43.75,  "cached": 4.375, "output": 350.0},
    "gpt-5.1":            {"input": 43.75,  "cached": 4.375, "output": 350.0},   # legacy-family proxy
    "gpt-5":              {"input": 43.75,  "cached": 4.375, "output": 350.0},   # legacy-family proxy
    "gpt-image-2.0":      {"input": 200.0,  "cached": 50.0,  "output": 750.0},   # image
    "gpt-image-2.0-text": {"input": 125.0,  "cached": 31.25, "output": 250.0},   # text
}

# Assumed token mix for the local estimate when no input/output breakdown
# is available from local history. Adjust to taste: (input, cached, output).
SPLIT = (0.80, 0.10, 0.10)


def norm_model(m):
    """Normalize a model string from local history to a rate-card key."""
    s = (m or "").lower().replace("_", "-").strip()
    # gpt-5.6-terra -> gpt-5.6-terra ; gpt-5.4-mini etc.
    if s in RATE_CARD:
        return s
    # try stripping suffixes like -codex / -max
    for cand in (s, s.replace("-codex", ""), s.replace("-codex-max", "-codex")):
        if cand in RATE_CARD:
            return cand
    return None


def load_chatgpt_token():
    """Return the ChatGPT access token from ~/.codex/auth.json (never printed)."""
    try:
        with open(CODEX_AUTH) as f:
            d = json.load(f)
        tok = (d.get("tokens") or {}).get("access_token")
        return tok or None
    except Exception:
        return None


def fetch_live_status():
    """Query the ChatGPT backend for Codex plan/limits/credits."""
    tok = load_chatgpt_token()
    if not tok:
        return {"status": "error", "message": "No ChatGPT token in ~/.codex/auth.json"}
    headers = {
        "Authorization": f"Bearer {tok}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Origin": "https://chatgpt.com",
        "Referer": "https://chatgpt.com/",
    }
    req = urllib.request.Request(USAGE_URL, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"status": "error", "message": f"HTTP {e.code}: {e.read().decode().strip()[:200]}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

    rl = data.get("rate_limit") or {}
    win = rl.get("primary_window") or {}
    credits = data.get("credits") or {}
    reset_at = win.get("reset_at")
    return {
        "status": "ok",
        "account": data.get("email"),
        "plan": data.get("plan_type"),
        "rate_limit": {
            "allowed": rl.get("allowed"),
            "limit_reached": rl.get("limit_reached"),
            "used_percent": win.get("used_percent"),
            "window_seconds": win.get("limit_window_seconds"),
            "reset_at_epoch": reset_at,
            "reset_at": datetime.fromtimestamp(reset_at, tz=timezone.utc).isoformat() if reset_at else None,
            "secondary_window": rl.get("secondary_window"),
        },
        "credits": {
            "has_credits": credits.get("has_credits"),
            "unlimited": credits.get("unlimited"),
            "balance": credits.get("balance"),
            "overage_limit_reached": credits.get("overage_limit_reached"),
        },
        "spend_control_reached": (data.get("spend_control") or {}).get("reached"),
        "code_review_rate_limit": data.get("code_review_rate_limit"),
    }


def fetch_local_usage(days):
    """Read per-model token usage from local Codex CLI history."""
    if not os.path.isfile(CODEX_DB):
        return {"status": "error", "message": f"Codex DB not found: {CODEX_DB}"}
    try:
        con = sqlite3.connect(f"file:{CODEX_DB}?mode=ro", uri=True)
        cur = con.cursor()
        cutoff_ms = (datetime.now().timestamp() - days * 86400) * 1000
        cur.execute(
            """SELECT COALESCE(model,'unknown'), COUNT(*), SUM(tokens_used)
               FROM threads
               WHERE model_provider='openai' AND created_at_ms > ?
               GROUP BY COALESCE(model,'unknown')
               ORDER BY 3 DESC""",
            (int(cutoff_ms),),
        )
        rows = cur.fetchall()
        con.close()
    except sqlite3.Error as e:
        return {"status": "error", "message": str(e)}

    per_model = []
    total_tokens = 0
    total_credits_min = 0.0
    total_credits_max = 0.0
    total_credits_est = 0.0
    for model, n, tokens in rows:
        tokens = int(tokens or 0)
        if tokens <= 0:
            continue
        total_tokens += tokens
        key = norm_model(model)
        if key:
            rates = RATE_CARD[key]
            t_m = tokens / 1e6
            c_min = t_m * rates["cached"]          # cheap lower bound (all cached)
            c_max = t_m * rates["output"]          # upper bound (all output)
            i, ca, o = SPLIT
            c_est = t_m * (i * rates["input"] + ca * rates["cached"] + o * rates["output"])
            total_credits_min += c_min
            total_credits_max += c_max
            total_credits_est += c_est
            per_model.append({
                "model": model,
                "sessions": n,
                "tokens": tokens,
                "rate_card_match": key,
                "credits_est": round(c_est, 1),
                "credits_range": [round(c_min, 1), round(c_max, 1)],
            })
        else:
            per_model.append({
                "model": model,
                "sessions": n,
                "tokens": tokens,
                "rate_card_match": None,
                "credits_est": None,
                "credits_range": None,
            })

    return {
        "status": "ok",
        "days": days,
        "total_tokens": total_tokens,
        "total_sessions": sum(m["sessions"] for m in per_model),
        "credits_est": round(total_credits_est, 1),
        "credits_range": [round(total_credits_min, 1), round(total_credits_max, 1)],
        "split_assumption": SPLIT,
        "per_model": per_model,
    }


def fmt_tokens(n):
    return f"{int(n):,}"


def print_pretty(data):
    live = data["live"]
    local = data["local"]
    print("  🧮 Rate card: token-based (credits per 1M tokens), updated 2026-08-07")
    print("     https://help.openai.com/en/articles/20001106-codex-rate-card")
    print()
    if live.get("status") == "ok":
        print(f"  📋 Plan:        {live['plan'].title()}")
        rl = live["rate_limit"]
        used = rl.get("used_percent")
        limit_reached = rl.get("limit_reached")
        if limit_reached:
            print(f"  🚫 Limit:       ⛔ REACHED — usage limit hit")
        elif used is not None:
            bar = "█" * int(used / 5) + "░" * (20 - int(used / 5))
            print(f"  📊 Weekly:      {bar} {used}% used (window ~{rl.get('window_seconds', 0)//86400}d)")
        else:
            print(f"  📊 Weekly:      allowed={rl.get('allowed')}")
        if rl.get("reset_at"):
            print(f"  🔄 Resets:      {rl['reset_at']}")
        cr = live["credits"]
        if cr.get("unlimited"):
            print(f"  ♾️  Credits:     Unlimited")
        else:
            print(f"  💳 Credits:     balance {cr.get('balance')} | has_credits={cr.get('has_credits')}")
    else:
        print(f"  ⚠️  Live status unavailable: {live.get('message')}")

    print()
    if local.get("status") == "ok":
        d = local["days"]
        print(f"  📈 Local CLI usage (last {d}d): {fmt_tokens(local['total_tokens'])} tokens, {local['total_sessions']} sessions")
        for m in local["per_model"]:
            extra = ""
            if m["credits_est"] is not None:
                extra = f" → ~{m['credits_est']} cr ({m['credits_range'][0]}–{m['credits_range'][1]})"
            match = m["rate_card_match"] or "no rate card match"
            print(f"    • {m['model']}: {fmt_tokens(m['tokens'])} tok, {m['sessions']} sess [{match}]{extra}")
        print(f"  🧾 Estimated credits: ~{local['credits_est']} (range {local['credits_range'][0]}–{local['credits_range'][1]})")
        print(f"     Assumed mix in/out: {local['split_assumption']} — edit SPLIT in codex.py if needed")
        print(f"     💡 ~$100–200/dev/month avg; typical GPT-5.6-Sol task ≈ 5–40 cr")
    else:
        print(f"  ⚠️  Local usage unavailable: {local.get('message')}")


def print_verbose(data):
    print_pretty(data)
    print("  Raw response:")
    print(json.dumps(data, indent=2))


def main():
    live = fetch_live_status()
    local = fetch_local_usage(30)
    data = {"live": live, "local": local}

    if "--json" in sys.argv:
        print(json.dumps(data, indent=2))
    elif "--verbose" in sys.argv:
        print_verbose(data)
    else:
        print_pretty(data)


if __name__ == "__main__":
    main()
