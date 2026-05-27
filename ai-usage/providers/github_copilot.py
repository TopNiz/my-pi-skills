#!/usr/bin/env python3
"""
GitHub Copilot Status Checker

Reads the OAuth refresh token from pi's auth.json (github-copilot.refresh),
then queries GitHub's internal Copilot token endpoint to get subscription info,
and the Copilot API to count available models.

Token lookup order:
  1. GITHUB_COPILOT_KEY env var
  2. ~/.pi/agent/.env  (GITHUB_COPILOT_KEY=ghu_...)
  3. ~/.pi/agent/auth.json  →  github-copilot.refresh
  4. gh CLI  (gh auth token)

Endpoints used:
  GET https://api.github.com/copilot_internal/v2/token
    Auth: token <refresh_token>
    Returns: sku, features enabled, fresh short-lived access token

  GET https://api.githubcopilot.com/models
    Auth: Bearer <access_token>
    Headers: Editor-Version, Editor-Plugin-Version, User-Agent
    Returns: list of available models

Usage:
  ./github_copilot.py              # Pretty output
  ./github_copilot.py --json       # Raw JSON response
  ./github_copilot.py --verbose    # Pretty + raw JSON
"""

import json
import os
import subprocess
import sys
import time
import urllib.request


AUTH_FILE = os.path.expanduser("~/.pi/agent/auth.json")
ENV_FILE  = os.path.expanduser("~/.pi/agent/.env")

EDITOR_HEADERS = {
    "Editor-Version":        "vscode/1.95.0",
    "Editor-Plugin-Version": "copilot/1.247.0",
    "User-Agent":            "GithubCopilot/1.247.0",
    "Accept":                "application/json",
}

SKU_LABELS = {
    "yearly_subscriber_quota":   "Individual — Yearly",
    "monthly_subscriber_quota":  "Individual — Monthly",
    "free_subscriber_quota":     "Free Tier",
    "business":                  "Copilot Business",
    "enterprise":                "Copilot Enterprise",
}


# ── Key discovery ─────────────────────────────────────────────────────────────

def get_refresh_token():
    """Return a GitHub OAuth token (ghu_...) usable for the Copilot internal endpoint."""
    # 1. Env var
    val = os.environ.get("GITHUB_COPILOT_KEY")
    if val:
        return val

    # 2. .env file
    if os.path.isfile(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line.startswith("GITHUB_COPILOT_KEY="):
                    return line.split("=", 1)[1].strip('"').strip("'")

    # 3. pi auth.json — github-copilot.refresh
    if os.path.isfile(AUTH_FILE):
        try:
            with open(AUTH_FILE) as f:
                auth = json.load(f)
            tok = auth.get("github-copilot", {}).get("refresh", "")
            if tok:
                return tok
        except (json.JSONDecodeError, KeyError):
            pass

    # 4. gh CLI
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True, text=True, timeout=5,
        )
        tok = result.stdout.strip()
        if tok:
            return tok
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None


# ── API calls ─────────────────────────────────────────────────────────────────

def _get(url, headers):
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read()), None
    except urllib.error.HTTPError as e:
        body = e.read().decode().strip()[:200]
        return None, f"HTTP {e.code}: {body}"
    except Exception as e:
        return None, str(e)


def fetch_copilot_token(refresh_token):
    """Call /copilot_internal/v2/token to get subscription info + fresh access token."""
    headers = dict(EDITOR_HEADERS)
    headers["Authorization"] = f"token {refresh_token}"
    data, err = _get(
        "https://api.github.com/copilot_internal/v2/token",
        headers,
    )
    if err:
        return None, err
    return data, None


def fetch_models(access_token):
    """Call the Copilot models endpoint to get available model list."""
    headers = dict(EDITOR_HEADERS)
    headers["Authorization"] = f"Bearer {access_token}"
    data, err = _get("https://api.githubcopilot.com/models", headers)
    if err:
        return [], err
    return data.get("data", []), None


# ── Subscription info extraction ──────────────────────────────────────────────

def parse_access_token(token_str):
    """Parse the semicolon-separated access token fields into a dict."""
    fields = {}
    for part in token_str.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            fields[k] = v
    return fields


def build_result(token_data, models):
    """Build a unified result dict from the token response."""
    sku = token_data.get("sku", "unknown")
    plan_label = SKU_LABELS.get(sku, sku)
    individual = token_data.get("individual", False)

    # Determine endpoints to figure out account type
    endpoints = token_data.get("endpoints", {})
    proxy_ep   = endpoints.get("proxy", "")

    expires_at = token_data.get("expires_at", 0)
    expires_ts = int(expires_at) if expires_at else 0
    now        = int(time.time())
    expires_in = expires_ts - now  # seconds (short-lived access token; not the subscription)

    features = {
        "chat":          token_data.get("chat_enabled", False),
        "code_review":   token_data.get("code_review_enabled", False),
        "agent_mode":    token_data.get("agent_mode_auto_approval", False),
        "mcp":           "mcp=1" in token_data.get("token", ""),
        "codesearch":    token_data.get("codesearch", False),
        "xcode":         token_data.get("xcode", False),
    }

    public_suggestions = token_data.get("public_suggestions", "unknown")

    # quota: null means unlimited (full subscriber)
    limited_quotas = token_data.get("limited_user_quotas")

    return {
        "status": "ok",
        "sku": sku,
        "plan_label": plan_label,
        "individual": individual,
        "public_suggestions": public_suggestions,
        "limited_quotas": limited_quotas,
        "features": features,
        "models_count": len(models),
        "models": [m["id"] for m in models],
        "token_expires_at": expires_ts,
        "token_expires_in_seconds": expires_in,
    }


# ── Output formatters ─────────────────────────────────────────────────────────

def print_pretty(data):
    if data.get("status") == "error":
        print(f"  ❌ {data['message']}")
        return

    plan   = data.get("plan_label", "?")
    models = data.get("models_count", 0)
    feats  = data.get("features", {})
    pub    = data.get("public_suggestions", "?")
    quota  = data.get("limited_quotas")

    print(f"  ✅ Plan:     {plan}")
    if quota is None:
        print(f"  ♾️  Quota:    Unlimited (full subscriber)")
    else:
        print(f"  📊 Quota:    {quota}")
    print(f"  🤖 Models:   {models} available")
    print(f"  💬 Chat:     {'enabled' if feats.get('chat') else 'disabled'}")
    print(f"  🕵️  Agent:    {'enabled' if feats.get('agent_mode') else 'disabled'}")
    print(f"  🔍 Search:   {'enabled' if feats.get('codesearch') else 'disabled'}")
    print(f"  🔒 Public code suggestions: {pub}")


def print_verbose(data):
    if data.get("status") == "error":
        print(f"  Status:   ❌ Error")
        print(f"  Message:  {data['message']}")
    else:
        plan   = data.get("plan_label", "?")
        sku    = data.get("sku", "?")
        models = data.get("models_count", 0)
        feats  = data.get("features", {})
        pub    = data.get("public_suggestions", "?")
        quota  = data.get("limited_quotas")
        exp_in = data.get("token_expires_in_seconds", 0)

        print(f"  Status:     ✅ Active")
        print(f"  Plan:       {plan}")
        print(f"  SKU:        {sku}")
        print(f"  Quota:      {'Unlimited' if quota is None else quota}")
        print(f"  Models:     {models} available")
        print(f"  Chat:       {'yes' if feats.get('chat') else 'no'}")
        print(f"  Agent mode: {'yes' if feats.get('agent_mode') else 'no'}")
        print(f"  MCP:        {'yes' if feats.get('mcp') else 'no'}")
        print(f"  Code review:{'yes' if feats.get('code_review') else 'no'}")
        print(f"  Codesearch: {'yes' if feats.get('codesearch') else 'no'}")
        print(f"  Xcode:      {'yes' if feats.get('xcode') else 'no'}")
        print(f"  Public code:{pub}")
        print(f"  Token TTL:  {exp_in}s ({exp_in // 60}min)")
    print()
    print("  Raw response:")
    print(json.dumps(data, indent=2))


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    refresh_token = get_refresh_token()
    if not refresh_token:
        print("  ⚠️  No GitHub Copilot token found.", file=sys.stderr)
        print("     Set GITHUB_COPILOT_KEY in ~/.pi/agent/.env, or ensure ~/.pi/agent/auth.json", file=sys.stderr)
        print("     contains github-copilot.refresh, or install gh CLI.", file=sys.stderr)
        sys.exit(1)

    token_data, err = fetch_copilot_token(refresh_token)
    if err:
        result = {"status": "error", "message": err}
    else:
        access_token = token_data.get("token", "")
        models, _   = fetch_models(access_token) if access_token else ([], None)
        result      = build_result(token_data, models)

    if "--json" in sys.argv:
        print(json.dumps(result, indent=2))
    elif "--verbose" in sys.argv:
        print_verbose(result)
    else:
        print_pretty(result)


if __name__ == "__main__":
    main()
