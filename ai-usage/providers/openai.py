#!/usr/bin/env python3
"""
OpenAI Usage & Cost Checker

Reads the admin API key from macOS keychain (service: 'openai-admin-key'),
then queries the Usage and Costs APIs for the last 30 days.

Usage:
  ./openai.py                  # Pretty output
  ./openai.py --json           # Raw JSON response
  ./openai.py --verbose        # Pretty + raw JSON
"""

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone


def get_admin_key():
    """Read OpenAI admin key from multiple sources."""
    # 1. Environment variable (cross-platform)
    env_key = os.environ.get("OPENAI_ADMIN_KEY")
    if env_key:
        return env_key

    # 2. pi .env file (~/.pi/agent/.env)
    pi_env = os.path.expanduser("~/.pi/agent/.env")
    if os.path.isfile(pi_env):
        with open(pi_env) as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENAI_ADMIN_KEY="):
                    return line.split("=", 1)[1].strip('"')

    # 3. File-based key (Linux: ~/.config/openai/admin-key)
    key_file = os.path.expanduser("~/.config/openai/admin-key")
    if os.path.isfile(key_file):
        with open(key_file) as f:
            file_key = f.read().strip()
            if file_key:
                return file_key

    # 3. macOS keychain (macOS only)
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "openai-admin-key", "-w"],
            capture_output=True, text=True, timeout=5,
        )
        key = result.stdout.strip()
        if key:
            return key
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def fetch_all(url, params, headers):
    """Fetch paginated data from an OpenAI API endpoint."""
    all_data = []
    page_cursor = None
    while True:
        p = dict(params)
        if page_cursor:
            p["page"] = page_cursor
        qs = "&".join(f"{k}={v}" for k, v in p.items())
        full_url = f"{url}?{qs}"
        req = urllib.request.Request(full_url, headers=headers)
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            d = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return {"status": "error", "message": f"HTTP {e.code}: {e.read().decode().strip()[:200]}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        all_data.extend(d.get("data", []))
        page_cursor = d.get("next_page")
        if not page_cursor:
            break
    return all_data


def fetch_usage(key):
    """Fetch token usage data from the Completions Usage API."""
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    today = datetime.now(timezone.utc)
    end_ts = int(today.timestamp())
    start_ts = int(today.timestamp()) - (30 * 24 * 3600)

    # Completions Usage API
    usage_data = fetch_all(
        "https://api.openai.com/v1/organization/usage/completions",
        {"start_time": start_ts, "end_time": end_ts, "bucket_width": "1d", "limit": 31},
        headers,
    )
    if isinstance(usage_data, dict) and usage_data.get("status") == "error":
        return usage_data

    total_input_tokens = 0
    total_output_tokens = 0
    total_cached_tokens = 0
    total_requests = 0
    for bucket in usage_data:
        for r in bucket.get("results", []):
            total_input_tokens += int(r.get("input_tokens", 0) or 0)
            total_output_tokens += int(r.get("output_tokens", 0) or 0)
            total_cached_tokens += int(r.get("input_cached_tokens", 0) or 0)
            total_requests += int(r.get("num_model_requests", 0) or 0)

    # Costs API
    cost_data = fetch_all(
        "https://api.openai.com/v1/organization/costs",
        {"start_time": start_ts, "end_time": end_ts, "bucket_width": "1d", "limit": 31},
        headers,
    )
    if isinstance(cost_data, dict) and cost_data.get("status") == "error":
        return cost_data

    total_cost = 0.0
    project_costs = {}
    for bucket in cost_data:
        for r in bucket.get("results", []):
            amt = float(r.get("amount", {}).get("value", 0) or 0)
            proj = r.get("project_name", "Unknown")
            if amt > 0:
                project_costs[proj] = project_costs.get(proj, 0) + amt
            total_cost += amt

    return {
        "status": "ok",
        "total_cost": round(total_cost, 4),
        "cost_currency": "usd",
        "project_costs": project_costs,
        "period_start": datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat(),
        "period_end": today.isoformat(),
        "usage": {
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "cached_tokens": total_cached_tokens,
            "num_requests": total_requests,
        },
    }


def fmt_num(n):
    """Format a number with commas."""
    return f"{int(n):,}"


def print_pretty(data):
    """Pretty-print the usage report."""
    if data.get("status") == "error":
        print(f"  ❌ {data['message']}")
        return

    total = data.get("total_cost", 0)
    usage = data.get("usage", {})
    input_tok = usage.get("input_tokens", 0)
    output_tok = usage.get("output_tokens", 0)
    cached_tok = usage.get("cached_tokens", 0)
    requests = usage.get("num_requests", 0)

    if total:
        print(f"  💰 Cost (30d):  ${total} USD")
        projects = data.get("project_costs", {})
        for p, c in sorted(projects.items(), key=lambda x: -x[1]):
            print(f"    - {p}: ${c:.4f}")
    else:
        print(f"  💰 Cost (30d):  $0.00 USD")
    print(f"  📊 Tokens:     {fmt_num(input_tok)} in / {fmt_num(output_tok)} out / {fmt_num(cached_tok)} cached")
    print(f"  🔄 Requests:   {fmt_num(requests)}")


def print_verbose(data):
    """Verbose output with raw JSON."""
    if data.get("status") == "error":
        print(f"  Status:       ❌ Error")
        print(f"  Message:      {data['message']}")
    else:
        print(f"  Status:       ✅ Active")
        total = data.get("total_cost", 0)
        usage = data.get("usage", {})
        print(f"  Period:       {data['period_start']} → {data['period_end']}")
        print(f"  Total cost:   ${total} USD")
        projects = data.get("project_costs", {})
        if projects:
            print(f"  By project:")
            for p, c in sorted(projects.items(), key=lambda x: -x[1]):
                print(f"    {p}: ${c:.4f}")
        print(f"  Input tokens:  {fmt_num(usage.get('input_tokens', 0))}")
        print(f"  Output tokens: {fmt_num(usage.get('output_tokens', 0))}")
        print(f"  Cached tokens: {fmt_num(usage.get('cached_tokens', 0))}")
        print(f"  Requests:      {fmt_num(usage.get('num_requests', 0))}")
    print(f"  Raw response:")
    print(json.dumps(data, indent=2))


def main():
    key = get_admin_key()
    if not key:
        print("  ⚠️  No OpenAI admin key found.", file=sys.stderr)
        print("     macOS: security add-generic-password -a \"$USER\" -s openai-admin-key -w \"sk-your-key\" -U", file=sys.stderr)
        print("     Linux:  echo 'sk-your-key' > ~/.config/openai/admin-key && chmod 600 ~/.config/openai/admin-key", file=sys.stderr)
        print("     Any OS: export OPENAI_ADMIN_KEY=sk-your-key", file=sys.stderr)
        sys.exit(1)

    data = fetch_usage(key)

    if "--json" in sys.argv:
        print(json.dumps(data, indent=2))
    elif "--verbose" in sys.argv:
        print_verbose(data)
    else:
        print_pretty(data)


if __name__ == "__main__":
    main()
