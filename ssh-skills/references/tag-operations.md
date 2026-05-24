# Tag Operations

Leveraging the tag system in your SSH config for bulk orchestration.

---

## 🏷️ Understanding Your Tags

Your config uses three tags. Each determines the **RemoteCommand** and **TTY** behavior:

| Tag | RemoteCommand | TTY | Use Case |
|-----|--------------|-----|----------|
| `linux` | `tmux -u new -A -s ssh_tmux` | yes | Interactive terminal |
| `macos` | `/opt/homebrew/bin/tmux -u new -A -s ssh_tmux` | yes | Interactive terminal |
| `vscode` | `none` | no | VS Code Remote |

---

## 📋 Listing Hosts by Tag

### Manual extraction

```bash
# Linux hosts (robust awk approach — not fragile grep -B1)
awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="linux" {print h}' ~/.ssh/config

# macOS hosts
awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="macos" {print h}' ~/.ssh/config

# VS Code hosts
awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="vscode" {print h}' ~/.ssh/config

# All hosts (excluding wildcard)
grep "^Host " ~/.ssh/config | grep -v "\*" | awk '{print $2}'
```

### Prepared function (add to .bashrc/.zshrc)

```bash
ssh-hosts() {
  local tag="${1:-}"
  if [ -n "$tag" ] && [ "$tag" != "all" ]; then
    awk -v t="$tag" '/^Host /{h=\$2} \$1=="Tag" && \$2==t {print h}' ~/.ssh/config
  else
    grep "^Host " ~/.ssh/config | grep -v "\*" | awk '{print $2}'
  fi
}

# Usage:
# ssh-hosts           → all hosts
# ssh-hosts linux     → Linux hosts
# ssh-hosts macos     → macOS hosts
```

---

## 🔄 Bulk Run on Tagged Hosts

### Run command on all hosts of a tag

```bash
# Sequential
for host in $(awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="linux" {print h}' ~/.ssh/config); do
  echo "═══ $host ═══"
  ssh "$host" "uptime" 2>/dev/null || echo "  (unreachable)"
done

# Parallel (xargs -P)
awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="linux" {print h}' ~/.ssh/config | \
  xargs -I{} -P4 ssh {} "uptime"
```

### Run command on all hosts (all tags)

```bash
# Exclude github and wildcard
grep "^Host " ~/.ssh/config | grep -v "github\|*" | awk '{print $2}' | \
  while read host; do
    echo "--- $host ---"
    ssh -o ConnectTimeout=5 "$host" "hostname" 2>/dev/null || echo "  (unreachable)"
  done
```

---

## ✅ Bulk Connectivity Check

```bash
# Check all hosts
for host in $(grep "^Host " ~/.ssh/config | grep -v "github\|*" | awk '{print $2}'); do
  if ssh -o ConnectTimeout=3 -o BatchMode=yes "$host" "echo OK" 2>/dev/null | grep -q OK; then
    echo "✅ $host"
  else
    echo "❌ $host"
  fi
done
```

### Color-coded version

```bash
for host in $(grep "^Host " ~/.ssh/config | grep -v "github\|*" | awk '{print $2}'); do
  if ssh -o ConnectTimeout=3 -o BatchMode=yes "$host" "echo OK" 2>/dev/null | grep -q OK; then
    echo -e "\033[32m✅ $host\033[0m"
  else
    echo -e "\033[31m❌ $host\033[0m"
  fi
done
```

---

## 📤 Bulk File Transfer

### Push file to all tagged hosts

```bash
# Copy a file to all Linux hosts
for host in $(awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="linux" {print h}' ~/.ssh/config); do
  rsync -avz ./deploy.sh "$host":/tmp/
done
```

### Pull files from all tagged hosts

```bash
# Pull logs from all Linux hosts
mkdir -p ./remote-logs
for host in $(awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="linux" {print h}' ~/.ssh/config); do
  rsync -avz "$host":/var/log/syslog "./remote-logs/$host-syslog"
done
```

---

## 📊 Tag-Based Inventory

### Generate an inventory report

```bash
{
  echo "📋 SSH Infrastructure Report"
  echo "============================"
  echo ""
  for tag in linux macos vscode; do
    echo "--- $tag hosts ---"
    for host in $(awk -v t="$tag" '/^Host /{h=\$2} \$1=="Tag" && \$2==t {print h}' ~/.ssh/config); do
      info=$(ssh -o ConnectTimeout=3 -G "$host" 2>/dev/null | grep -E "^(hostname|user)" | paste - -)
      reachable=$(ssh -o ConnectTimeout=2 -o BatchMode=yes "$host" "echo alive" 2>/dev/null)
      status="❌"
      [ "$reachable" = "alive" ] && status="✅"
      echo "  $status $host → $info"
    done
    echo ""
  done
} > ~/ssh-inventory.txt

echo "Inventory saved to ~/ssh-inventory.txt"
```

---

## 🧩 Extending the Tag System

### Adding new tags

```bash
# To add a "backup" tag:
# 1. Add to a host definition:
#    Host <host-name>
#      Tag backup
#
# 2. Create a Match block:
#    Match tagged backup
#      RemoteCommand /usr/local/bin/backup-agent

# Multiple tags (not natively supported, but can be simulated):
# Host <host-name>
#   Tag linux
#   # Can add custom directive like:
#   #   IncludeTag backup
```

### Environment-based tagging

```bash
# Add to ~/.ssh/config:
# Host <prod-server>
#   Tag linux
#   # Uncomment for prod-specific behavior:
#   # Match uses first-match-wins, so put specific before generic
#
# Host <dev-server>
#   Tag linux
```
