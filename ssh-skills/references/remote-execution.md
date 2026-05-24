# Remote Execution

Running commands, scripts, and orchestrating operations on remote hosts.

---

## 🎯 Single Commands

### Basic execution

```bash
# Simple command
ssh <host-alias> "whoami"

# Multiple commands chained
ssh <host-alias> "date && uptime && free -h"

# With proper quoting for pipes
ssh <host-alias> "ps aux | grep nginx | wc -l"

# Multi-line (semicolons or newlines with quoting)
ssh <host-alias> "
  echo '=== System Info ==='
  uname -a
  echo '=== Disk ==='
  df -h /
  echo '=== Memory ==='
  free -h
"
```

### Capture output

```bash
# Save remote output to local file
ssh <host-alias> "journalctl -u nginx --since today" > ./nginx-log-$(date +%Y%m%d).txt

# Pipe through local commands
ssh <host-alias> "cat /var/log/syslog" | grep "error" | head -20

# Parse remote JSON
ssh <host-alias> "curl -s http://localhost:8080/health" | jq '.status'
```

### Environment and context

```bash
# Pass environment variable
ssh <host-alias> "MY_VAR=hello env | grep MY_VAR"

# Run command in specific directory
ssh <host-alias> "cd /var/www && ls -la"

# Use sudo (with NOPASSWD in sudoers on remote)
ssh <host-alias> "sudo systemctl restart nginx"

# With tty allocation for sudo prompts
ssh -t <host-alias> "sudo systemctl restart nginx"
```

---

## 📜 Scripts — Remote Execution

### Push-and-run pattern

```bash
# Copy script, then execute
scp ./deploy.sh <host-alias>:/tmp/deploy.sh
ssh <host-alias> "chmod +x /tmp/deploy.sh && /tmp/deploy.sh"
ssh <host-alias> "rm /tmp/deploy.sh"  # cleanup
```

### Pipe script directly to bash (no temp file)

```bash
# Feed script to remote shell via stdin
cat ./deploy.sh | ssh <host-alias> "bash -s"

# With arguments
cat ./deploy.sh | ssh <host-alias> "bash -s -- --env=prod --force"

# Inline script (useful for simple tasks)
ssh <host-alias> "bash -s" <<'REMOTESCRIPT'
  set -e
  echo "=== Update & Upgrade ==="
  sudo apt update && sudo apt upgrade -y
  echo "=== Cleanup ==="
  sudo apt autoremove -y
  echo "=== Done ==="
REMOTESCRIPT
```

### Herdoc with local variable expansion

```bash
# With $VARIABLE expansion on LOCAL side (double-quoted delimiter)
USER="nizarayed"
ssh <host-alias> "bash -s" <<REMOTESCRIPT
  echo "Running as: $USER"
REMOTESCRIPT

# Without expansion on LOCAL side (quoted delimiter)
ssh <host-alias> "bash -s" <<'REMOTESCRIPT'
  echo "Remote HOME: \$HOME"
REMOTESCRIPT
```

---

## 🏗️ Orchestration — Multiple Hosts

### Sequential execution

```bash
# Same command on all known hosts
for host in <remote-server-1> <ubuntu-server> <mac-silicon>; do
  echo "═══════════════ $host ═══════════════"
  ssh "$host" "uptime"
  echo ""
done
```

### Parallel execution (xargs)

```bash
# Run on all Linux hosts in parallel (max 4 at a time)
awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="linux" {print h}' ~/.ssh/config | \
  xargs -I{} -P4 ssh {} "uptime"

# Capture output with host labeling
awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="linux" {print h}' ~/.ssh/config | \
  xargs -I{} -P2 sh -c 'echo "--- {} ---"; ssh {} "free -h"'
```

### Parallel execution (GNU parallel)

```bash
# Install: brew install parallel (macOS) / apt install parallel (Linux)

# Run on all hosts
parallel -j4 ssh {} "uptime" ::: <host-1> <host-2> <host-3>

# With output grouped by host
parallel --group -j4 ssh {} "uptime && free -h" ::: <host-1> <host-2>
```

### SSH multiplexed fan-out

```bash
# Start all master connections first (fast subsequent access)
for host in $(grep "^Host " ~/.ssh/config | grep -v "github\|*" | awk '{print $2}'); do
  ssh -fNM "$host" 2>/dev/null  # -f = background, -N = no command, -M = master mode
done

# Now run commands — each is nearly instant
for host in $(grep "^Host " ~/.ssh/config | grep -v "github\|*" | awk '{print $2}'); do
  ssh "$host" "uptime"
done
```

---

## 🩺 Health Check / Monitoring

### Quick system overview

```bash
ssh <host-alias> "
  echo '├─ Uptime:     ' \$(uptime -p)
  echo '├─ Load:       ' \$(cat /proc/loadavg | awk '{print \$1, \$2, \$3}')
  echo '├─ Memory:     ' \$(free -h | awk '/^Mem:/ {print \$3 \"/\" \$2}')
  echo '├─ Disk (/):   ' \$(df -h / | awk 'NR==2 {print \$3 \"/\" \$2}')
  echo '├─ Processes:  ' \$(ps aux | wc -l)
  echo '└─ IP:         ' \$(hostname -I | awk '{print \$1}')
"
```

### Service status check

```bash
# Check if a service is running on multiple hosts
for host in <vm-fedora> <vm-ubuntu>; do
  status=$(ssh "$host" "systemctl is-active nginx" 2>/dev/null || echo "unreachable")
  echo "$host → nginx: $status"
done
```

### Disk usage alert

```bash
# Find hosts with disk usage over 80%
for host in $(grep "^Host " ~/.ssh/config | grep -v "github\|*" | awk '{print $2}'); do
  usage=$(ssh "$host" "df -h / | awk 'NR==2 {print +\\\$5}'" 2>/dev/null)
  [ -n "$usage" ] && [ "$usage" -gt 80 ] && echo "⚠️  $host: ${usage}% disk usage"
done
```

---

## 🛠️ Maintenance Operations

### System update all hosts

```bash
# Update all Linux hosts
for host in $(awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="linux" {print h}' ~/.ssh/config); do
  echo "=== Updating $host ==="
  ssh "$host" "sudo apt update && sudo apt upgrade -y && sudo apt autoremove -y" 2>&1
  echo "✅ $host updated"
done
```

### Reboot management

```bash
# Reboot multiple hosts (with confirmation)
echo "Hosts to reboot:"
awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="linux" {print h}' ~/.ssh/config
read -p "Continue with reboot? (y/N) " confirm
if [ "$confirm" = "y" ]; then
  for host in $(awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="linux" {print h}' ~/.ssh/config); do
    echo "Rebooting $host..."
    ssh "$host" "sudo reboot" 2>/dev/null &
    sleep 1
  done
  wait
fi
```

### Install package on all hosts

```bash
# Parallel install
awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="linux" {print h}' ~/.ssh/config | \
  xargs -I{} -P4 ssh {} "sudo apt install -y htop tmux git"
```
