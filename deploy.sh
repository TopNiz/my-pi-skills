#!/usr/bin/env bash
# Deploy skills to a remote host via rsync
#
# Usage:
#   ./deploy.sh <ssh-host>         # Deploy skills to remote host
#   ./deploy.sh codimeo.com        # Example
#   ./deploy.sh pc-vm-fedora-1.local
#
# Requires:
#   - SSH access configured in ~/.ssh/config
#   - ~/.pi/agent/.env on the remote (copy manually or use scp)
set -euo pipefail

HOST="$1"
SKILLS_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -z "$HOST" ]; then
  echo "Usage: $0 <ssh-host>"
  echo "Deploys skills to <ssh-host>:~/.agents/skills/"
  exit 1
fi

echo "📦 Deploying skills to $HOST..."

# Rsync skills (exclude sensitive/config files)
rsync -avz --delete \
  -e "ssh -o RemoteCommand=none -o RequestTTY=no" \
  --exclude='.git/' \
  --exclude='.env' \
  --exclude='config.json' \
  --exclude='__pycache__/' \
  --exclude='.playwright-cli/' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  "$SKILLS_DIR/" \
  "$HOST:~/.agents/skills/"

# Also deploy the .env file if it exists locally
ENV_SRC="$HOME/.pi/agent/.env"
ENV_DST="$HOST:~/.pi/agent/.env"
if [ -f "$ENV_SRC" ]; then
  echo "🔑 Deploying ~/.pi/agent/.env..."
  scp -o RemoteCommand=none -o RequestTTY=no "$ENV_SRC" "$ENV_DST"
  ssh -o RemoteCommand=none -o RequestTTY=no "$HOST" "chmod 600 ~/.pi/agent/.env"
fi

echo "✅ Done! Skills deployed to $HOST"
