#!/usr/bin/env bash
# AI Usage Checker — check costs, balance, and status across all your AI providers.
#
# Orchestrates provider-specific Python scripts under providers/.
# Each provider script supports: --json, --verbose
#
# Usage:
#   ./check-usage.sh                   # Show all providers
#   ./check-usage.sh openai            # OpenAI only
#   ./check-usage.sh deepseek          # DeepSeek only
#   ./check-usage.sh ollama            # Ollama Cloud only
#   ./check-usage.sh --verbose         # Show all with full details
#   ./check-usage.sh --json            # Output raw JSON for all
#   ./check-usage.sh --help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROVIDERS_DIR="$SCRIPT_DIR/providers"

PROVIDER_SCRIPTS=(
  "openai:openai.py"
  "deepseek:deepseek.py"
  "ollama:ollama.py"
  "github-copilot:github_copilot.py"
)

OUTPUT_MODE="pretty"  # pretty, json, verbose
FILTER=""             # empty = all providers

# --- Option parsing ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    openai|deepseek|ollama|github-copilot) FILTER="$1"; shift ;;
    --json)    OUTPUT_MODE="json"; shift ;;
    --verbose) OUTPUT_MODE="verbose"; shift ;;
    -h|--help)
      echo "AI Usage Checker — check all your AI accounts at a glance"
      echo ""
      echo "Usage: $0 [provider] [--json|--verbose]"
      echo ""
      echo "Providers (omit to show all):"
      echo "  openai           OpenAI API (costs, token usage)"
      echo "  deepseek         DeepSeek API (balance, credits)"
      echo "  ollama           Ollama Cloud (key validity, model count)"
      echo "  github-copilot   GitHub Copilot (plan, features, models)"
      echo ""
      echo "Options:"
      echo "  --json        Output raw JSON responses"
      echo "  --verbose     Show detailed info with raw data"
      echo "  -h, --help    Show this help"
      echo ""
      echo "Examples:"
      echo "  $0                    # All providers"
      echo "  $0 deepseek           # DeepSeek only"
      echo "  $0 --verbose          # All providers with details"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# --- Determine which provider scripts to run ---
run_list=()
for entry in "${PROVIDER_SCRIPTS[@]}"; do
  name="${entry%%:*}"
  script="${entry#*:}"
  if [ -z "$FILTER" ] || [ "$FILTER" = "$name" ]; then
    run_list+=("$name:$PROVIDERS_DIR/$script")
  fi
done

# ============================================================
#  PRETTY / VERBOSE mode
# ============================================================
if [ "$OUTPUT_MODE" != "json" ]; then
  echo ""
  echo "━━━ AI Usage Report ━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""

  PRETTY_FLAG=""
  [ "$OUTPUT_MODE" = "verbose" ] && PRETTY_FLAG="--verbose"

  for entry in "${run_list[@]}"; do
    name="${entry%%:*}"
    script="${entry#*:}"

    case "$name" in
      openai)          echo "🔵 OpenAI (API)" ;;
      deepseek)         echo "🟢 DeepSeek" ;;
      ollama)           echo "🟠 Ollama Cloud" ;;
      github-copilot)   echo "🐙 GitHub Copilot" ;;
    esac

    if [ -x "$script" ]; then
      # Run with --json and pipe to Python for error handling
      result=$("$script" $PRETTY_FLAG 2>&1)
      exit_code=$?
      if [ $exit_code -ne 0 ]; then
        echo "  ⚠️  Script error (exit $exit_code)"
        echo "$result" | sed 's/^/    /'
      else
        echo "$result"
      fi
    else
      echo "  ⚠️  Script not found: $script"
    fi
    echo ""
  done

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "📊 For detailed billing:"
  echo "   OpenAI:           https://platform.openai.com/usage"
  echo "   DeepSeek:         https://platform.deepseek.com"
  echo "   Ollama:           https://ollama.com/settings/billing"
  echo "   GitHub Copilot:   https://github.com/settings/copilot"
  echo ""

# ============================================================
#  JSON mode — merge all provider outputs into one JSON object
# ============================================================
else
  tmpdir=$(mktemp -d)
  trap 'rm -rf "$tmpdir"' EXIT

  for entry in "${run_list[@]}"; do
    name="${entry%%:*}"
    script="${entry#*:}"
    if [ -x "$script" ]; then
      "$script" --json > "$tmpdir/$name.json" 2>/dev/null || true
    fi
  done

  python3 -c "
import json, os

tmpdir = '$tmpdir'
result = {}
providers = ['openai', 'deepseek', 'ollama', 'github-copilot']

for p in providers:
    path = os.path.join(tmpdir, f'{p}.json')
    if os.path.exists(path):
        with open(path) as f:
            content = f.read().strip()
            result[p] = json.loads(content) if content else {'status': 'skipped'}
    else:
        result[p] = {'status': 'skipped'}

print(json.dumps(result, indent=2))
"
fi
