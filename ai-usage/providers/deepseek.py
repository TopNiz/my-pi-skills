#!/usr/bin/env python3
"""
DeepSeek API Balance Checker

Reads the API key from the DEEPSEEK_KEY env var (from ~/.local/share/pi/auth-keys.env) or pi's auth.json as fallback.
then queries the balance endpoint.

Usage:
  ./deepseek.py                # Pretty output
  ./deepseek.py --json         # Raw JSON response
  ./deepseek.py --verbose      # Pretty + raw JSON
"""

import json
import os
import sys
import urllib.request


AUTH_FILE = os.path.expanduser("~/.pi/agent/auth.json")
ENV_FILE = os.path.expanduser("~/.pi/agent/.env")


def get_api_key():
    """Read DeepSeek API key from env var, then env file, then pi's auth.json."""
    # 1. Environment variable (sourced from auth-keys.env)
    env_key = os.environ.get("DEEPSEEK_KEY")
    if env_key:
        return env_key

    # 2. Source env file directly
    try:
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line.startswith("DEEPSEEK_KEY="):
                    return line.split("=", 1)[1].strip('"')
    except FileNotFoundError:
        pass

    # 3. Fallback: pi's auth.json
    try:
        with open(AUTH_FILE) as f:
            auth = json.load(f)
        return auth["deepseek"]["key"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return None


def fetch_balance(key):
    """Fetch account balance from DeepSeek API."""
    try:
        req = urllib.request.Request(
            "https://api.deepseek.com/user/balance",
            headers={"Authorization": f"Bearer {key}"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode().strip()[:200]
        return {"status": "error", "message": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def print_pretty(data):
    """Pretty-print the balance report."""
    if data.get("status") == "error":
        print(f"  ❌ {data['message']}")
        return

    available = data.get("is_available", False)
    if available:
        for info in data.get("balance_infos", []):
            total = info.get("total_balance", "0")
            cur = info.get("currency", "USD")
            print(f"  💰 Total balance:  ${total} {cur}")
            print(f"  ✅ Account:        Active")
    else:
        print(f"  ⚠️  Account unavailable or error")


def print_verbose(data):
    """Verbose output with raw JSON."""
    if data.get("status") == "error":
        print(f"  Status:       ❌ Error")
        print(f"  Message:      {data['message']}")
    else:
        available = data.get("is_available", False)
        print(f"  Status:       {'✅ Available' if available else '❌ Unavailable'}")
        for info in data.get("balance_infos", []):
            cur = info.get("currency", "USD")
            total = info.get("total_balance", "0")
            granted = info.get("granted_balance", "0")
            topped = info.get("topped_up_balance", "0")
            print(f"  Currency:      {cur}")
            print(f"  Total:         ${total}")
            print(f"  Granted:       ${granted}")
            print(f"  Topped up:     ${topped}")
    print()
    print("  Raw response:")
    print(json.dumps(data, indent=2))


def main():
    key = get_api_key()
    if not key:
        print("  ⚠️  No DeepSeek API key found. Check DEEPSEEK_KEY env var or ~/.pi/agent/.env", file=sys.stderr)
        sys.exit(1)

    data = fetch_balance(key)

    if "--json" in sys.argv:
        print(json.dumps(data, indent=2))
    elif "--verbose" in sys.argv:
        print_verbose(data)
    else:
        print_pretty(data)


if __name__ == "__main__":
    main()
