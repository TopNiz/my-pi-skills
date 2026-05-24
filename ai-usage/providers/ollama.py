#!/usr/bin/env python3
"""
Ollama Cloud API Checker

Reads the API key from the OLLAMA_CLOUD_KEY env var (from ~/.local/share/pi/auth-keys.env) or opencode's auth.json as fallback.
then queries:
  1. GET /api/tags        — list available cloud models
  2. POST /api/generate   — test inference with a lightweight model to get usage stats

Usage:
  ./ollama.py                  # Pretty output
  ./ollama.py --json           # Raw JSON response
  ./ollama.py --verbose        # Pretty + raw JSON + model list
"""

import json
import os
import sys
import urllib.request


AUTH_FILE = os.path.expanduser("~/.local/share/opencode/auth.json")
ENV_FILE = os.path.expanduser("~/.pi/agent/.env")
CLOUD_BASE = "https://ollama.com/api"


def get_api_key():
    """Read Ollama Cloud API key from env var, then env file, then opencode auth.json."""
    # 1. Environment variable (sourced from auth-keys.env or set manually)
    env_key = os.environ.get("OLLAMA_CLOUD_KEY")
    if env_key:
        return env_key

    # 2. Source env file directly
    try:
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line.startswith("OLLAMA_CLOUD_KEY="):
                    return line.split("=", 1)[1].strip('"')
    except FileNotFoundError:
        pass

    # 3. Fallback: opencode auth.json
    try:
        with open(AUTH_FILE) as f:
            auth = json.load(f)
        return auth["ollama-cloud"]["key"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return None


def api_call(method, path, headers, body=None):
    """Make an API call and return parsed JSON, or an error dict."""
    url = f"{CLOUD_BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode().strip()[:300]
        return {"status": "error", "message": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def fetch_data(key):
    """Fetch both model list and usage stats."""
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    # 1. Tags — list available cloud models
    tags = api_call("GET", "/tags", headers)
    if isinstance(tags, dict) and tags.get("status") == "error":
        return tags

    models = tags.get("models", [])
    model_count = len(models)

    # 2. Generate — make a tiny inference to get usage metrics
    # Use a lightweight model with a minimal prompt
    usage_stats = {}
    gen_result = api_call(
        "POST", "/generate", headers,
        body={
            "model": "gemma3:4b",
            "prompt": "hi",
            "stream": False,
        },
    )
    if isinstance(gen_result, dict) and gen_result.get("status") == "error":
        usage_stats = {
            "status": "rate_limited",
            "message": gen_result["message"],
        }
    elif gen_result.get("done"):
        usage_stats = {
            "status": "ok",
            "total_duration_ns": gen_result.get("total_duration"),
            "load_duration_ns": gen_result.get("load_duration"),
            "prompt_eval_count": gen_result.get("prompt_eval_count"),
            "prompt_eval_duration_ns": gen_result.get("prompt_eval_duration"),
            "eval_count": gen_result.get("eval_count"),
            "eval_duration_ns": gen_result.get("eval_duration"),
            "done_reason": gen_result.get("done_reason"),
        }

    return {
        "status": "ok",
        "model_count": model_count,
        "models": [m.get("name", "?") for m in models],
        "usage": usage_stats,
    }


def fmt_duration(ns):
    """Format nanoseconds to a human-readable string."""
    if ns is None:
        return "?"
    if ns < 1_000:
        return f"{ns} ns"
    elif ns < 1_000_000:
        return f"{ns/1_000:.1f} µs"
    elif ns < 1_000_000_000:
        return f"{ns/1_000_000:.1f} ms"
    else:
        return f"{ns/1_000_000_000:.2f} s"


def print_pretty(data):
    """Pretty-print the cloud status."""
    if data.get("status") == "error":
        print(f"  ❌ {data['message']}")
        return

    print(f"  ✅ API key valid — {data['model_count']} cloud models accessible")

    usage = data.get("usage", {})
    if usage.get("status") == "ok":
        print(f"  📊 Usage stats (gemma3:4b test inference):")
        print(f"     Prompt tokens:  {usage.get('prompt_eval_count', '?')}")
        print(f"     Output tokens:  {usage.get('eval_count', '?')}")
        print(f"     Total time:     {fmt_duration(usage.get('total_duration_ns'))}")
    elif usage.get("status") == "rate_limited":
        print(f"  ⚠️  Usage stats unavailable (free tier rate limit)")
    else:
        print(f"  ⚠️  Usage stats unavailable (no test inference made)")


def print_verbose(data):
    """Verbose output with model list and raw JSON."""
    if data.get("status") == "error":
        print(f"  Status:       ❌ Error")
        print(f"  Message:      {data['message']}")
    else:
        print(f"  Status:       ✅ Available")
        print(f"  Cloud models: {data['model_count']}")

        # Print first 15 models
        for name in data.get("models", [])[:15]:
            print(f"    - {name}")
        rest = len(data.get("models", [])) - 15
        if rest > 0:
            print(f"    ... and {rest} more")

        usage = data.get("usage", {})
        print()
        if usage.get("status") == "ok":
            print(f"  Test inference (gemma3:4b):")
            print(f"    Prompt tokens:         {usage.get('prompt_eval_count', '?')}")
            print(f"    Output tokens:         {usage.get('eval_count', '?')}")
            print(f"    Total duration:        {fmt_duration(usage.get('total_duration_ns'))}")
            print(f"    Load duration:         {fmt_duration(usage.get('load_duration_ns'))}")
            print(f"    Prompt eval duration:  {fmt_duration(usage.get('prompt_eval_duration_ns'))}")
            print(f"    Eval duration:         {fmt_duration(usage.get('eval_duration_ns'))}")
            print(f"    Done reason:           {usage.get('done_reason', '?')}")
        elif usage.get("status") == "rate_limited":
            print(f"  Test inference: ⚠️ Rate limited — {usage.get('message', '')}")

    print()
    print("  Raw response:")
    out = json.dumps(data, indent=2)
    lines = out.split("\n")
    if len(lines) > 50:
        print("\n".join(lines[:45]))
        print("    ... (truncated)")
    else:
        print(out)


def main():
    key = get_api_key()
    if not key:
        print("  ⚠️  No Ollama Cloud key found. Check OLLAMA_CLOUD_KEY env var or ~/.pi/agent/.env", file=sys.stderr)
        sys.exit(1)

    data = fetch_data(key)

    if "--json" in sys.argv:
        print(json.dumps(data, indent=2))
    elif "--verbose" in sys.argv:
        print_verbose(data)
    else:
        print_pretty(data)


if __name__ == "__main__":
    main()
