#!/usr/bin/env bash
# Push skills to GitHub, then pull on remote hosts.
#
# Usage:
#   ./deploy.sh                              # Push local changes to GitHub
#   ./deploy.sh codimeo.com                  # Push + pull on remote
#   ./deploy.sh pc-vm-fedora-1.local         # Push + pull on remote
#   ./deploy.sh codimeo.com pc-vm-fedora-1.local  # Push + pull on multiple remotes
#
# .env files are NOT pushed or deployed — each machine manages its own secrets.
# After first clone on a remote:
#   cp ~/.agents/skills/ai-usage/.env.example ~/.pi/agent/.env
#   # Then edit ~/.pi/agent/.env with your keys
set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SKILLS_DIR"

# Check for uncommitted changes
if ! git diff --quiet --cached || ! git diff --quiet; then
  echo "📝 Committing local changes..."
  git add -A
  git commit -m "Update skills — $(date '+%Y-%m-%d %H:%M')"
fi

echo "⬆️  Pushing to GitHub..."
git push

# If no remotes specified, we're done
if [ $# -eq 0 ]; then
  echo "✅ Pushed to GitHub. No remotes to update."
  exit 0
fi

# Pull on each remote host
for HOST in "$@"; do
  echo ""
  echo "🌐 Pulling on $HOST..."
  ssh -o RemoteCommand=none -o RequestTTY=no "$HOST" \
    "cd ~/.agents/skills && git pull"
  echo "✅ $HOST updated"
done

echo ""
echo "🎉 All done!"
echo ""
echo "📌 Remember: each machine needs its own ~/.pi/agent/.env with secrets."
echo "   Copy template: cp ~/.agents/skills/ai-usage/.env.example ~/.pi/agent/.env"
