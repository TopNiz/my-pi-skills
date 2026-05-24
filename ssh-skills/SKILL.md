---
name: ssh-skills
description: Comprehensive SSH/SSh/SCP/RSYNC operations — connect, transfer files, run remote commands, manage tunnels, and orchestrate tag-based bulk operations across your infrastructure. Designed for your homelab and remote servers.
---

# SSH Skills — Complete Reference

A full suite of SSH operations built around your SSH config. This skill handles everything from simple connections to bulk operations across tagged host groups.

> **🔒 Security note**: All examples use obfuscated placeholders. Your actual SSH config contains real hostnames, IPs, and key paths — those are never exposed.

---

## 📋 Quick Reference — Your Infrastructure (Obfuscated)

Your SSH config defines hosts organized by **OS tags** and **purpose tags**:

| Tag | Host Pattern | OS | Purpose |
|-----|-------------|----|---------|
| `linux` | `<remote-server-1>`, `<vm-fedora>`, `<vm-ubuntu>`, `<ubuntu-server>`, `<ubuntu-desktop>` | Linux | Interactive + TMUX |
| `macos` | `<mac-pro>`, `<mac-silicon>` | macOS | Interactive + TMUX (Homebrew) |
| `vscode` | `vscode-*` variants | All | Non-interactive, no TMUX |
| *(none)* | `<windows-pc>`, `<windows-laptop>` | Windows | Simple shell |

**Pattern**: `Host <name>` for shell access — `Host vscode-<name>` for VS Code Remote.

---

## 🚀 Core Commands

### 1. Quick Connections

```bash
# Connect to any host by its SSH Host alias
ssh <host-alias>

# Examples:
ssh <remote-server-1>         # Remote Linux → auto-attaches to tmux
ssh <mac-silicon>             # Local macOS   → auto-attaches to tmux (Homebrew)
ssh <windows-pc>              # Windows       → plain shell
ssh vscode-<mac-pro>          # VS Code mode  → non-interactive
ssh github.com                # GitHub        → git operations
```

### 2. Execute Remote Commands

```bash
# Run a single command and exit
ssh <host-alias> "command"

# Agent-friendly / automation-safe form:
# Use this when the SSH config defines RemoteCommand or requests a TTY/tmux.
# It disables automatic interactive startup commands and avoids pseudo-TTY allocation.
ssh -o RemoteCommand=none -o RequestTTY=no <host-alias> "command"

# Examples:
ssh -o RemoteCommand=none -o RequestTTY=no <remote-server-1> "uptime && free -h"
ssh -o RemoteCommand=none -o RequestTTY=no <vm-fedora> "systemctl status nginx"
ssh -o RemoteCommand=none -o RequestTTY=no <ubuntu-server> "df -h /"
ssh -o RemoteCommand=none -o RequestTTY=no <mac-silicon> "sw_vers"

# With environment variables
ssh -o RemoteCommand=none -o RequestTTY=no <host-alias> "ENV=value ./script.sh"

# Pipe local data to remote stdin
cat local-file.txt | ssh -o RemoteCommand=none -o RequestTTY=no <host-alias> "cat > /tmp/remote-file.txt"
```

> **Agent note**: Many personal SSH configs start tmux/shell setup via `RemoteCommand` and may force a TTY for interactive use. That is convenient for humans but inconvenient for agents and scripts. For non-interactive remote checks, prefer `-o RemoteCommand=none -o RequestTTY=no` so the requested command runs directly and exits cleanly.

### 3. File Transfer — SCP

```bash
# Push: local → remote
scp <local-path> <host-alias>:<remote-path>

# Pull: remote → local
scp <host-alias>:<remote-path> <local-path>

# Recursive directory copy
scp -r <local-dir>/ <host-alias>:<remote-dir>/

# Examples:
scp ./deploy.sh <remote-server-1>:/opt/scripts/
scp <ubuntu-server>:/var/log/syslog ./logs/
scp -r ./configs/ <vm-fedora>:/etc/my-app/
```

### 4. File Transfer — RSYNC (resumable, efficient)

```bash
# Sync local → remote (archive, compress, verbose)
rsync -avz <local-dir>/ <host-alias>:<remote-dir>/

# Sync remote → local
rsync -avz <host-alias>:<remote-dir>/ <local-dir>/

# Dry-run first (see what would change)
rsync -avz --dry-run <local-dir>/ <host-alias>:<remote-dir>/

# Delete files on destination that don't exist on source
rsync -avz --delete <local-dir>/ <host-alias>:<remote-dir>/

# Exclude patterns
rsync -avz --exclude='.git/' --exclude='node_modules/' <dir>/ <host-alias>:<dir>/
```

### 5. SSH Tunneling / Port Forwarding

```bash
# Local port forwarding: local:PORT → remote:HOST:PORT
ssh -L <local-port>:<target-host>:<target-port> <host-alias>

# Remote port forwarding: remote:PORT → local:HOST:PORT
ssh -R <remote-port>:<local-host>:<local-port> <host-alias>

# Dynamic SOCKS proxy
ssh -D <local-port> <host-alias>

# Examples:
# Access remote web app via local browser
ssh -L 8080:localhost:80 <remote-server-1>
# Now open http://localhost:8080 in your browser

# Expose local dev server to remote machine
ssh -R 9000:localhost:3000 <vm-fedora>
# Remote can now access http://localhost:9000

# SOCKS proxy through remote server
ssh -D 1080 <remote-server-1>
# Configure browser to use SOCKS5 proxy at localhost:1080
```

### 6. Jump Host / ProxyJump

```bash
# Connect through a bastion/jump host
ssh -J <jump-host> <target-host>

# Example (if you had a bastion):
# ssh -J <remote-server-1> <internal-server>

# In SSH config (not yet configured, but useful):
# Host <internal-server>
#   ProxyJump <remote-server-1>
```

---

## 🏷️ Tag-Based Bulk Operations

Your SSH config uses `Tag linux`, `Tag macos`, and `Tag vscode` — this enables powerful bulk operations.

### List hosts by tag (awk-based — robust, handles variable line distances)

```bash
# List all hosts with a specific tag
awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="linux" {print h}' ~/.ssh/config

# All macOS hosts
awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="macos" {print h}' ~/.ssh/config

# All VS Code hosts
awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="vscode" {print h}' ~/.ssh/config
```

> **Note**: Simple `grep -B1` doesn't work reliably because some hosts have extra directives (like `RemoteCommand`) between `HostName` and `Tag`. The `awk` approach tracks the last `Host` line and prints it when a matching `Tag` is found — regardless of distance.

### Run command on all hosts of a tag

```bash
# Using a simple for loop
for host in $(awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="linux" {print h}' ~/.ssh/config); do
  echo "=== $host ==="
  ssh "$host" "uptime"
done

# Parallel execution with xargs
awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="linux" {print h}' ~/.ssh/config | \
  xargs -I{} -P4 ssh {} "uptime"
```

### Check connectivity to all hosts

```bash
grep "^Host " ~/.ssh/config | grep -v "github\|*" | awk '{print $2}' | \
  while read host; do
    ssh -o ConnectTimeout=3 -o BatchMode=yes "$host" "echo OK" 2>/dev/null \
      && echo "✅ $host reachable" || echo "❌ $host unreachable"
  done
```

---

## 🔄 ControlMaster — Persistent Connection Management

Your config uses `ControlMaster auto` with `ControlPersist yes`. This means SSH keeps a background connection alive for rapid reconnections.

### Manage master connections

```bash
# List all active master sockets
ls -la ~/.ssh/master-*

# Check if a specific host has an active master connection
ls -la ~/.ssh/master-*@<host-alias>*

# Manually stop a master connection (force new auth)
ssh -O stop <host-alias>

# Check status of a master connection
ssh -O check <host-alias>

# Force a new connection (bypass master)
ssh -S none <host-alias>
```

### Why this matters

```bash
# First connection: normal speed (establishes master)
time ssh <remote-server-1> "echo hello"

# Subsequent connections: nearly instant (reuses master)
time ssh <remote-server-1> "echo hello"   # ~10x faster
```

---

## 🪟 TMUX Session Management

Your config auto-attaches to `tmux` for `linux` and `macos` tagged hosts. This means you always resume where you left off.

### Working with tmux inside SSH

```bash
# Connect → auto-attaches to tmux session named "ssh_tmux"
ssh <remote-server-1>

# Inside tmux (keybindings):
# Ctrl+B d        → Detach (SSH stays open, you can reconnect later)
# Ctrl+B c        → New window
# Ctrl+B n/p      → Next/previous window
# Ctrl+B ,        → Rename window
# Ctrl+B w        → List windows
# Ctrl+B %        → Split vertically
# Ctrl+B "        → Split horizontally

# If you need a fresh tmux session on the remote:
ssh <remote-server-1> "tmux new -s temp_session"
```

---

## 📡 Advanced Use Cases

### 1. One-shot file copy + command execution

```bash
# Copy a script and run it remotely
scp ./deploy.sh <remote-server-1>:/tmp/deploy.sh && \
  ssh <remote-server-1> "chmod +x /tmp/deploy.sh && /tmp/deploy.sh"
```

### 2. SSH config syntax check

```bash
# Validate your SSH config after editing
ssh -G <any-host> > /dev/null && echo "✅ Config valid" || echo "❌ Config invalid"

# View the effective config for a specific host
ssh -G <remote-server-1>
```

### 3. SSH key operations

```bash
# Add key to SSH agent (your config has AddKeysToAgent yes)
ssh-add ~/.ssh/<key-name>

# List keys in agent
ssh-add -l

# Test connection with verbose (debug auth issues)
ssh -vvv <host-alias>
```

### 4. VS Code Remote — SSH

```bash
# VS Code uses the vscode-* hosts (non-interactive, no tmux)
# From terminal:
code --remote ssh-remote+vscode-<host-alias> <path-on-remote>

# Example:
# code --remote ssh-remote+vscode-<ubuntu-server> /home/<user>/project
```

### 5. SCP with compression for slow links

```bash
scp -C <large-file> <remote-server-1>:~/
```

### 6. Keep SSH alive (prevent timeout)

```bash
# One-off: keep alive for 60 seconds
ssh -o ServerAliveInterval=60 <host-alias>

# This is not in your current config, but useful for long-running sessions
```

---

## 📚 Reference Documents

For deeper dives into each topic, see the references:

| Document | Topics |
|----------|--------|
| [SSH Config Analysis](references/ssh-config-analysis.md) | Understanding your config structure, tags, match blocks |
| [Connection Management](references/connection-management.md) | Multiplexing, tunnels, jump hosts, keepalive |
| [File Transfer](references/file-transfer.md) | SCP, RSYNC patterns for all scenarios |
| [Remote Execution](references/remote-execution.md) | Single commands, scripts, parallel execution |
| [Tag Operations](references/tag-operations.md) | Bulk operations, orchestration, monitoring |
| [TMUX Integration](references/tmux-integration.md) | Session management, windows, automation |

---

## 🛠️ Helper Script

A companion script `ssh-helper.sh` provides shortcuts for common operations:

```bash
# List all hosts by tag
./ssh-helper.sh list linux
./ssh-helper.sh list macos
./ssh-helper.sh list all

# Run command on tagged hosts
./ssh-helper.sh run linux "uptime"
./ssh-helper.sh run macos "sw_vers"

# Check connectivity
./ssh-helper.sh ping all
./ssh-helper.sh ping vscode

# Copy file to tagged hosts
./ssh-helper.sh push linux ./file.txt /tmp/
./ssh-helper.sh pull linux /var/log/syslog ./logs/
```

---

## ⚙️ Configuration Tips

To add a new host to your SSH config:

```bash
# Template (replacing placeholders):
# Host <new-host-alias>
#   HostName <ip-or-domain>
#   User <username>
#   Tag <linux|macos|vscode>
```

To add VS Code support for a new host, create a second entry:

```
Host vscode-<new-host-alias>
  HostName <same-ip>
  Tag vscode
  # (VS Code non-interactive config is added by the Match tagged vscode block)
```

---

## 🔐 Security Best Practices

1. **Your config already does these right:**
   - ✅ `ForwardAgent no` by default (stops credential forwarding)
   - ✅ `IdentitiesOnly yes` (prevents key brute-force)
   - ✅ `PreferredAuthentications publickey` (password-less auth)
   - ✅ `ControlMaster auto` with persistent sockets

2. **Consider adding:**
   - `Host <remote-server-1>` with `PasswordAuthentication no` for internet-facing hosts
   - Different keys per host (`IdentityFile ~/.ssh/<host-specific-key>`)
   - `Match host <remote-server-1> !host localhost` for internet-facing hardening
