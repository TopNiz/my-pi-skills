#!/usr/bin/env bash
# ===========================================================================
# SSH Helper Script — for the ssh-skills pi agent skill
#
# Provides shortcuts for listing hosts, running commands, and transferring
# files across all hosts defined in ~/.ssh/config.
#
# Usage:
#   ./ssh-helper.sh list [tag]        # List hosts (optional: filter by tag)
#   ./ssh-helper.sh run <tag> <cmd>   # Run command on tagged hosts
#   ./ssh-helper.sh ping [tag]        # Check connectivity
#   ./ssh-helper.sh push <tag> <src> <dst>  # Copy file to tagged hosts
#   ./ssh-helper.sh pull <tag> <src> <dst>  # Copy file from tagged hosts
#   ./ssh-helper.sh info [host]       # Show effective config for a host
#   ./ssh-helper.sh help              # Show this help
# ===========================================================================

SSH_CONFIG="$HOME/.ssh/config"

usage() {
  cat <<EOF
SSH Helper — Operations across your SSH infrastructure

Usage: $(basename "$0") <command> [options]

Commands:
  list [tag]       List all hosts, or filter by tag (linux|macos|vscode)
  run <tag> <cmd>  Run a command on all hosts with the given tag
  ping [tag]       Test connectivity to hosts (optional: filter by tag)
  push <tag> <src> <dst>  Copy file/dir TO tagged hosts (uses rsync)
  pull <tag> <src> <dst>  Copy file/dir FROM tagged hosts (uses rsync)
  info [host]      Show effective SSH config for a host (or all)
  sockets           List active ControlMaster sockets
  help             Show this help message

Examples:
  $(basename "$0") list linux
  $(basename "$0") run linux "uptime"
  $(basename "$0") ping all
  $(basename "$0") push linux ./script.sh /tmp/
  $(basename "$0") pull linux /var/log/syslog ./logs/
EOF
}

error() {
  echo "❌ Error: $1" >&2
  exit 1
}

# ── List hosts by tag ──────────────────────────────────────────────────────
list_hosts() {
  local tag="$1"
  if [ -z "$tag" ] || [ "$tag" = "all" ]; then
    grep "^Host " "$SSH_CONFIG" | grep -v "\*" | awk '{print $2}'
  else
    # Use awk to find the Host line preceding a Tag match (handles variable distance)
    awk -v t="$tag" '
      /^Host / { current = $2 }
      $1 == "Tag" && $2 == t { print current }
    ' "$SSH_CONFIG"
  fi
}

# ── Run command on tag group ───────────────────────────────────────────────
run_cmd() {
  local tag="$1"; shift
  [ -z "$1" ] && error "Usage: $(basename "$0") run <tag> <command>"
  local cmd="$*"

  for host in $(list_hosts "$tag"); do
    echo "═══ $host ═══"
    ssh -o ConnectTimeout=5 "$host" "$cmd" 2>&1 || echo "  (unreachable)"
    echo ""
  done
}

# ── Ping / connectivity check ──────────────────────────────────────────────
ping_hosts() {
  local tag="$1"
  local hosts

  if [ -z "$tag" ] || [ "$tag" = "all" ]; then
    hosts=$(list_hosts "")
  else
    hosts=$(list_hosts "$tag")
  fi

  [ -z "$hosts" ] && error "No hosts found${tag:+ for tag '$tag'}"

  local reachable=0 total=0
  while IFS= read -r host; do
    [ -z "$host" ] && continue
    total=$((total + 1))
    if ssh -o ConnectTimeout=3 -o BatchMode=yes "$host" "echo OK" 2>/dev/null | grep -q OK; then
      echo "✅ $host"
      reachable=$((reachable + 1))
    else
      echo "❌ $host"
    fi
  done <<< "$hosts"

  echo ""
  echo "📊 $reachable/$total hosts reachable"
}

# ── Push file to tag group ─────────────────────────────────────────────────
push_file() {
  local tag="$1"; local src="$2"; local dst="$3"
  [ -z "$src" ] && error "Usage: $(basename "$0") push <tag> <src> <dst>"
  [ ! -e "$src" ] && error "Source '$src' does not exist"

  for host in $(list_hosts "$tag"); do
    echo "📤 $host:$dst"
    rsync -avz --progress "$src" "${host}:${dst}"
  done
}

# ── Pull file from tag group ──────────────────────────────────────────────
pull_file() {
  local tag="$1"; local src="$2"; local dst="$3"
  [ -z "$src" ] && error "Usage: $(basename "$0") pull <tag> <src> <dst>"
  mkdir -p "$dst" 2>/dev/null

  for host in $(list_hosts "$tag"); do
    echo "📥 $host:$src → $dst/$host/"
    rsync -avz --progress "${host}:${src}" "${dst}/${host}/"
  done
}

# ── Show info for a host ───────────────────────────────────────────────────
show_info() {
  local host="$1"
  if [ -n "$host" ]; then
    echo "═══ $host ═══"
    ssh -G "$host" 2>/dev/null | grep -E "^(hostname|user|port|identityfile|forwardagent)" | head -10
  else
    for host in $(list_hosts ""); do
      echo "═══ $host ═══"
      ssh -G "$host" 2>/dev/null | grep -E "^(hostname|user|port)" | head -5
      echo ""
    done
  fi
}

# ── List active ControlMaster sockets ──────────────────────────────────────
show_sockets() {
  local sockets=("$HOME/.ssh/master-"*)
  if [ -e "${sockets[0]}" ]; then
    echo "Active ControlMaster sockets:"
    ls -lh "$HOME/.ssh/master-"*
  else
    echo "No active ControlMaster sockets."
  fi
}

# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

CMD="${1:-help}"
shift 2>/dev/null

case "$CMD" in
  list)
    list_hosts "$1"
    ;;
  run)
    run_cmd "$@"
    ;;
  ping)
    ping_hosts "$1"
    ;;
  push)
    push_file "$@"
    ;;
  pull)
    pull_file "$@"
    ;;
  info)
    show_info "$1"
    ;;
  sockets)
    show_sockets
    ;;
  help|--help|-h)
    usage
    ;;
  *)
    error "Unknown command: $CMD\n$(usage)"
    ;;
esac
