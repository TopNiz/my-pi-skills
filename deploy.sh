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

confirm_continue() {
  local prompt="$1"

  if [ "${DEPLOY_ASSUME_YES:-}" = "1" ]; then
    echo "⚠️  DEPLOY_ASSUME_YES=1 set — continuing without interactive confirmation."
    return 0
  fi

  if [ ! -t 0 ]; then
    echo "❌ Confirmation required, but stdin is not interactive."
    echo "   Re-run in a terminal, or set DEPLOY_ASSUME_YES=1 if you intentionally accept the risk."
    exit 1
  fi

  local answer
  read -r -p "$prompt [y/N] " answer
  case "$answer" in
    y|Y|yes|YES|Yes) return 0 ;;
    *) echo "❌ Deploy cancelled."; exit 1 ;;
  esac
}

review_git_status_with_pi() {
  local status name_status diff_stat changed_paths sensitive_paths review_prompt review_output

  status="$(git -c color.status=false status --short --branch)"
  name_status="$(
    {
      git diff --name-status --cached
      git diff --name-status
      git ls-files --others --exclude-standard | sed 's/^/??\t/'
    } | sed '/^$/d'
  )"
  diff_stat="$(
    {
      echo "# staged diff --stat"
      git diff --stat --cached
      echo
      echo "# unstaged diff --stat"
      git diff --stat
    } | sed '/^$/d'
  )"
  changed_paths="$(
    {
      git diff --name-only --cached
      git diff --name-only
      git ls-files --others --exclude-standard
    } | sort -u
  )"

  echo "🔎 Git status before deploy:"
  printf '%s\n' "$status"
  if [ -n "$name_status" ]; then
    echo ""
    echo "Changed files that would be included by git add -A:"
    printf '%s\n' "$name_status"
  fi

  sensitive_paths="$(printf '%s\n' "$changed_paths" | grep -Ei '(^|/)(\.env|.*\.pem|.*\.key|id_rsa|id_ed25519|auth\.json|config\.json|user_preferences\.json|.*secret.*|.*credential.*|.*token.*)$' || true)"
  if [ -n "$sensitive_paths" ]; then
    echo ""
    echo "⚠️  Potentially sensitive paths detected in files Git may commit:"
    printf '%s\n' "$sensitive_paths"
    confirm_continue "Continue deploy despite potentially sensitive paths?"
  fi

  if ! command -v pi >/dev/null 2>&1; then
    echo ""
    echo "⚠️  pi command not found; cannot run no-session agent status review."
    confirm_continue "Continue deploy without pi review?"
    return 0
  fi

  review_prompt="$(cat <<EOF
You are reviewing a public GitHub repository deploy script before it auto-commits and pushes changes.

The deploy script will run: git add -A, git commit, git push. That means staged, unstaged, deleted, and untracked non-ignored files are all in scope.

Review the Git status summary below. Decide whether the deploy requires extra human caution before continuing. Caution is required when there are possible secrets, credentials, personal/private host details, generated artifacts, accidental deletions, large/binary files, local-only config, or surprising/unrelated changes.

Return exactly this structure:
CAUTION: yes|no
SUMMARY: one short sentence
REASONS:
- bullet list, or '- none'
RECOMMENDATION: continue|review first

Do not ask follow-up questions. Do not suggest commands unless caution is yes.

Git status --short --branch:
$status

Files/statuses that git add -A would include:
${name_status:-none}

Diff stats:
${diff_stat:-none}
EOF
)"

  echo ""
  echo "🤖 Asking pi for a no-session status review..."
  if review_output="$(pi --no-session --no-tools --no-extensions --no-skills --no-prompt-templates --no-context-files --mode text -p "$review_prompt" 2>&1)"; then
    printf '%s\n' "$review_output"
    if printf '%s\n' "$review_output" | grep -Eiq '^CAUTION:[[:space:]]*yes\b'; then
      echo ""
      confirm_continue "⚠️  pi flagged caution. Continue deploy anyway?"
    fi
  else
    echo "⚠️  pi review failed:"
    printf '%s\n' "$review_output"
    confirm_continue "Continue deploy without a successful pi review?"
  fi
}

# Check for uncommitted changes
if ! git diff --quiet --cached || ! git diff --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
  review_git_status_with_pi

  echo "📝 Committing local changes..."
  git add -A
  git commit -m "Update skills — $(date '+%Y-%m-%d %H:%M')"
else
  echo "🔎 Git status before deploy:"
  git -c color.status=false status --short --branch
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
