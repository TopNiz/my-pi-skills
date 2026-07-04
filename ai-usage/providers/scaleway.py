#!/usr/bin/env python3
"""
Scaleway Usage & Cost Checker

Uses the Scaleway CLI (`scw`) to fetch consumption data from the Billing API,
then aggregates costs by category — with special focus on AI/Generative APIs.

Credentials are read from the Scaleway config file (~/.config/scw/config.yaml)
which is the standard SDK/CLI location on macOS.

Usage:
  ./scaleway.py                # Pretty output
  ./scaleway.py --json         # Raw JSON response
  ./scaleway.py --verbose      # Pretty + raw JSON
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone


CONFIG_PATHS = [
    os.path.expanduser("~/.config/scw/config.yaml"),
    os.path.expanduser("~/.config/scw/cli.yaml"),
]

# Categories that contain AI/ML/GTB/observability resources
AI_KEYWORDS = [
    "llm", "generative", "ai ", "gen ", "chat", "embedding", "rerank",
    "response", "audio", "batch", "model",
]

# Scaleway product categories
CONSUMPTION_CATEGORIES = [
    "Compute", "BareMetal", "Instance", "Serverless", "Kubernetes",
    "Object Storage", "Block Storage", "File Storage",
    "Network", "Private Network", "Load Balancer",
    "Databases", "Managed Database",
    "Observability", "Logging", "Monitoring",
    "AI", "Generative APIs", "Models",
    "Containers", "Registry",
    "Domains", "DNS", "Web Hosting",
    "Email", "Transactional Email",
    "IoT Hub", "Queues", "Topics",
    "Security", "Secret Manager", "Key Manager",
    "Other",
]


def get_config():
    """Read Scaleway config from standard locations."""
    for path in CONFIG_PATHS:
        if os.path.isfile(path):
            return path
    return None


def parse_config_value(filepath, key):
    """Simple YAML value extractor for flat Scaleway config."""
    try:
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}:"):
                    return line.split(":", 1)[1].strip().strip('"').strip("'")
    except (FileNotFoundError, IOError):
        pass
    return None


def get_credentials():
    """Get organization ID and secret key from Scaleway config."""
    config_path = get_config()
    if not config_path:
        return None, None

    org_id = parse_config_value(config_path, "default_organization_id")
    secret_key = parse_config_value(config_path, "secret_key")

    if not org_id:
        org_id = parse_config_value(config_path, "organization_id")

    return org_id, secret_key


def fetch_consumption():
    """Fetch consumption data via Scaleway CLI."""
    # Try to get credentials from env first
    org_id = os.environ.get("SCW_ORGANIZATION_ID") or os.environ.get("SCW_DEFAULT_ORGANIZATION_ID")
    access_key = os.environ.get("SCW_ACCESS_KEY")
    secret_key = os.environ.get("SCW_SECRET_KEY")

    if not org_id or not (access_key or secret_key):
        # Fall back to config file
        config_path = get_config()
        if config_path:
            if not org_id:
                org_id = parse_config_value(config_path, "default_organization_id") or \
                          parse_config_value(config_path, "organization_id")
            secret_key = secret_key or parse_config_value(config_path, "secret_key")
            access_key = access_key or parse_config_value(config_path, "access_key")

    if not org_id:
        return {"status": "error", "message": "No Scaleway organization ID found. Check ~/.config/scw/config.yaml"}

    cmd = ["scw", "billing", "consumption", "list", "-o", "json"]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            err_msg = result.stderr.strip()[:300]
            return {"status": "error", "message": f"scw CLI error: {err_msg}"}

        stdout = result.stdout.strip()
        if not stdout:
            return {"status": "ok", "consumptions": [], "total_cost": 0, "categories": {}}

        # Try to find a JSON array [ ... ] or JSON object { ... }
        # The scw CLI without -D outputs pure JSON (array of consumptions)
        # With -D debug, it has extra text around the JSON
        for pair in (("[", "]"), ("{", "}")):
            first = stdout.find(pair[0])
            if first >= 0:
                # Find matching closing bracket
                depth = 0
                last = first
                for i in range(first, len(stdout)):
                    if stdout[i] == pair[0]:
                        depth += 1
                    elif stdout[i] == pair[1]:
                        depth -= 1
                        if depth == 0:
                            last = i
                            break
                if last > first:
                    try:
                        parsed = json.loads(stdout[first:last+1])
                        # If it's an array (direct consumption list), wrap it
                        if isinstance(parsed, list):
                            return {
                                "status": "ok",
                                "consumptions": parsed,
                                "total_cost": _calc_total(parsed),
                                "categories": _group_by_category(parsed),
                            }
                        # If it's an object (paginated response), extract consumptions
                        if isinstance(parsed, dict):
                            cons = parsed.get("consumptions", [])
                            return {
                                "status": "ok",
                                "consumptions": cons,
                                "total_cost": _calc_total(cons),
                                "categories": _group_by_category(cons),
                            }
                    except json.JSONDecodeError:
                        continue

        return {"status": "error", "message": "Cannot parse scw output as JSON"}

    except FileNotFoundError:
        return {"status": "error", "message": "scw CLI not found. Install Scaleway CLI first."}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "scw CLI timed out after 30s"}
    except json.JSONDecodeError as e:
        return {"status": "error", "message": f"JSON parse error: {e}"}


def _calc_total(consumptions):
    """Calculate total cost from consumption list."""
    total = 0
    for c in consumptions:
        value = c.get("value", {})
        units = int(value.get("units", 0) or 0)
        nanos = int(value.get("nanos", 0) or 0) / 1e9
        total += units + nanos
    return round(total, 6)


def _group_by_category(consumptions):
    """Group consumptions by category and calculate totals."""
    categories = {}
    for c in consumptions:
        cat = c.get("category_name", "Other")
        value = c.get("value", {})
        units = int(value.get("units", 0) or 0)
        nanos = int(value.get("nanos", 0) or 0) / 1e9
        cost = units + nanos
        if cat not in categories:
            categories[cat] = {"cost": 0, "items": []}
        categories[cat]["cost"] += cost
        categories[cat]["items"].append({
            "product": c.get("product_name", "Unknown"),
            "resource": c.get("resource_name", ""),
            "cost": round(cost, 6),
            "unit": c.get("unit", ""),
            "billed_quantity": c.get("billed_quantity", "0"),
        })

    # Round totals
    for cat in categories:
        categories[cat]["cost"] = round(categories[cat]["cost"], 6)

    return categories


def find_ai_cost(categories):
    """Find costs that match AI/Generative API patterns."""
    ai_cost = 0
    ai_items = []
    for cat, data in categories.items():
        cat_lower = cat.lower()
        is_ai_cat = any(kw in cat_lower for kw in ["ai", "gen", "llm", "model", "observ"])
        for item in data["items"]:
            is_ai_prod = any(kw in item.get("product", "").lower() for kw in AI_KEYWORDS)
            if is_ai_cat or is_ai_prod:
                ai_cost += item["cost"]
                ai_items.append(item)
    return round(ai_cost, 6), ai_items


def print_pretty(data):
    """Pretty-print the usage report."""
    if data.get("status") == "error":
        print(f"  ⚠️  {data['message']}")
        return

    categories = data.get("categories", {})
    total_cost = data.get("total_cost", 0)
    ai_cost, ai_items = find_ai_cost(categories)

    if total_cost:
        print(f"  💰 Total cost:     €{total_cost:.6f} EUR")
    else:
        print(f"  💰 Total cost:     €0.00 EUR (no current usage)")

    # AI/Generative APIs highlight
    if ai_cost > 0:
        print(f"  🤖 AI/Gen APIs:    €{ai_cost:.6f} EUR")
        for item in ai_items[:5]:
            print(f"     - {item['product']}: €{item['cost']:.6f}")
        if len(ai_items) > 5:
            print(f"     ... and {len(ai_items) - 5} more AI item(s)")

    # Cost by category
    if categories:
        sorted_cats = sorted(categories.items(), key=lambda x: -x[1]["cost"])
        print(f"  📊 By category:")
        for cat, info in sorted_cats:
            print(f"     {cat}: €{info['cost']:.6f}")
    else:
        print(f"  📊 No consumption data for current period")


def print_verbose(data):
    """Verbose output with raw JSON."""
    if data.get("status") == "error":
        print(f"  Status:       ❌ Error")
        print(f"  Message:      {data['message']}")
        print(f"  Raw response:")
        print(json.dumps(data, indent=2))
        return

    categories = data.get("categories", {})
    total_cost = data.get("total_cost", 0)
    ai_cost, ai_items = find_ai_cost(categories)

    print(f"  Status:       ✅ Active")
    print(f"  Total cost:   €{total_cost:.6f} EUR")

    if ai_cost > 0:
        print(f"  AI/Gen APIs:  €{ai_cost:.6f} EUR ({len(ai_items)} items)")
        for item in ai_items:
            print(f"    - {item['product']} ({item.get('resource', '')}): €{item['cost']:.6f}")

    if categories:
        print(f"  Categories ({len(categories)}):")
        sorted_cats = sorted(categories.items(), key=lambda x: -x[1]["cost"])
        for cat, info in sorted_cats:
            print(f"    {cat}: €{info['cost']:.6f} ({len(info['items'])} items)")
            for item in info["items"][:3]:
                print(f"      - {item['product']}: €{item['cost']:.6f} {item.get('unit', '')}x{item.get('billed_quantity', '')}")
            if any(len(i["items"]) > 3 for n, i in sorted_cats if n == cat):
                print(f"      ... and more")
    else:
        print(f"  No consumption data")

    print()
    print("  Raw response:")
    print(json.dumps(data, indent=2))


def main():
    data = fetch_consumption()

    if "--json" in sys.argv:
        print(json.dumps(data, indent=2))
    elif "--verbose" in sys.argv:
        print_verbose(data)
    else:
        print_pretty(data)


if __name__ == "__main__":
    main()
