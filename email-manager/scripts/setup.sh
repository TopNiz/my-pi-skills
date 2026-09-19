#!/bin/bash
# Email Manager Skill — Setup Script (uv-based)
#
# Run once per machine: chmod +x setup.sh && ./setup.sh
#
# Dependencies live in ../pyproject.toml and are installed by uv into
# ../.venv. Do not use "pip install --target": on Windows pip stages wheels in
# a mkdtemp() tree (mode 0o700) and moves them into place, which stamps an
# owner-only, inheritance-breaking DACL on every installed file.

set -e

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_FILE="$SKILL_DIR/scripts/config.json"
CONFIG_TEMPLATE="$SKILL_DIR/scripts/config.template.json"

echo "📧 Email Manager — Setup"
echo "========================"
echo ""

# 1. Validate prerequisites
if ! command -v uv &>/dev/null; then
    echo "❌ uv is required (it manages the skill venv). Install it first:"
    echo "     https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi
echo "✅ uv found: $(uv --version)"

# 2. Install dependencies into the skill venv
echo ""
echo "📦 Syncing dependencies from pyproject.toml..."
(cd "$SKILL_DIR" && uv sync)
echo "✅ Environment ready: $SKILL_DIR/.venv"

# 3. Make scripts executable
chmod +x "$SKILL_DIR/scripts/"*.py "$SKILL_DIR/scripts/"*.sh 2>/dev/null || true
echo "✅ Scripts made executable"

# 4. Ensure the local config exists (never committed — see .gitignore)
if [ ! -f "$CONFIG_FILE" ]; then
    cp "$CONFIG_TEMPLATE" "$CONFIG_FILE"
    echo "✅ Created $CONFIG_FILE from the template"
    echo "   Review it (filters, invoice storage dir, protected senders, routing)."
else
    echo "✅ Config already present: $CONFIG_FILE"
fi

# 5. Authenticate with Google (OAuth2, one-time per machine)
echo ""
if python3 "$SKILL_DIR/scripts/auth.py" --check >/dev/null 2>&1; then
    echo "✅ Gmail already authenticated"
else
    echo "🔐 Not authenticated yet. Creating the Gmail OAuth2 token now."
    echo "   A browser window will open — approve access for the Gmail API."
    if [ -f "$SKILL_DIR/credentials.gmail.json" ] || [ -f "$SKILL_DIR/credentials.json" ]; then
        python3 "$SKILL_DIR/scripts/auth.py"
        echo "✅ Authenticated"
    else
        echo "⚠️  No OAuth client file found. Before authenticating:"
        echo "   1. Create a Desktop-app OAuth client in Google Cloud Console"
        echo "   2. Enable the Gmail API"
        echo "   3. Save the JSON as: $SKILL_DIR/credentials.gmail.json"
        echo "   Then run: python3 scripts/auth.py"
    fi
fi

echo ""
echo "🚀 Setup complete!"
echo ""
echo "To use, ask pi:"
echo "  \"Check my emails\"                    → Fetch & categorize"
echo "  \"Daily review\"                       → Summary of today"
echo "  \"Extract invoices\"                   → Find invoice emails"
echo "  \"What's urgent in my inbox?\"         → Flag urgent items"
echo ""
