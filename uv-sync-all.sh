#!/bin/bash
# Create or refresh the uv environment for every skill that declares
# Python dependencies (a pyproject.toml at the skill root).
#
# Safe to run anywhere: if uv is missing or a skill has no dependencies,
# it reports and moves on without failing. Used by deploy.sh after pulling
# on a remote host, and usable locally after cloning or bumping uv.lock.
#
# Usage:
#   ./uv-sync-all.sh            # sync every skill with a pyproject.toml
#   ./uv-sync-all.sh --upgrade  # refresh uv.lock before syncing

set -uo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

UPGRADE=0
[ "${1:-}" = "--upgrade" ] && UPGRADE=1

if ! command -v uv &>/dev/null; then
    echo "⚠️  uv not found — skipping skill environments."
    echo "   Install: https://docs.astral.sh/uv/getting-started/installation/"
    exit 0
fi

echo "🐍 uv $(uv --version 2>/dev/null | awk '{print $2}') — syncing skill environments"

found=0
failed=0
for manifest in */pyproject.toml; do
    [ -e "$manifest" ] || continue
    skill="${manifest%/pyproject.toml}"
    found=$((found + 1))
    printf '   %-22s ' "$skill"

    if [ "$UPGRADE" -eq 1 ]; then
        if ! (cd "$skill" && uv lock --upgrade >/dev/null 2>&1); then
            echo "⚠️  uv lock --upgrade failed"
            failed=$((failed + 1))
            continue
        fi
    fi

    if (cd "$skill" && uv sync --locked >/dev/null 2>&1); then
        echo "✅"
    else
        echo "⚠️  uv sync failed — run: (cd $skill && uv sync)"
        failed=$((failed + 1))
    fi
done

if [ "$found" -eq 0 ]; then
    echo "   no skill declares Python dependencies"
fi

if [ "$failed" -gt 0 ]; then
    echo "⚠️  $failed of $found environment(s) failed"
    exit 0   # never block a deploy on environment setup
fi

echo "✅ Skill environments ready"
