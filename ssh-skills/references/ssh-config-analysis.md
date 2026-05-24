# SSH Config Analysis

Understanding the structure of your SSH config to use it effectively.

---

## 🏗️ Architecture Overview

Your SSH config uses a **layered pattern**:

```
Global defaults (Host *)
  └── Match tagged vscode    → overrides for VS Code hosts
  └── Match tagged linux     → adds tmux for Linux hosts
  └── Match tagged macos     → adds tmux for macOS hosts (Homebrew path)
       └── Individual host definitions → inherit from above
```

---

## 📐 Tag System

Tags are the key to organization. They work through the `Match tagged` directive:

| Tag | Matched Hosts | Effect |
|-----|---------------|--------|
| `linux` | Remote servers, VMs (Fedora, Ubuntu) | `RemoteCommand tmux -u new -A -s ssh_tmux` |
| `macos` | MacBooks, iMacs | `RemoteCommand /opt/homebrew/bin/tmux -u new -A -s ssh_tmux` |
| `vscode` | All vscode-* prefixed hosts | `RequestTTY no`, `RemoteCommand none` |

### How to add a new host with tags

```bash
# Add these lines to ~/.ssh/config:

# Interactive shell version
Host <new-host>
  HostName <ip-address>
  User <username>
  Tag <linux|macos>

# VS Code remote version (if needed)
Host vscode-<new-host>
  HostName <ip-address>
  Tag vscode
```

---

## 🔍 Reading the Config Programmatically

### Extract all host aliases

```bash
grep "^Host " ~/.ssh/config | grep -v "\*" | awk '{print $2}'
```

### Extract hosts by tag

```bash
# Get all hosts with their tags (robust — handles variable line distances)
awk '/^Host /{h=\$2} \$1=="Tag" {print h, \$2}' ~/.ssh/config | column -t

# Output format: Host <name> Tag <tag>
```

### Get connection details for a specific host

```bash
ssh -G <host-alias> | grep -E "^(hostname|user|port|identityfile)"
```

### Count hosts by type

```bash
echo "Linux:  $(awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="linux" {c++} END {print c+0}' ~/.ssh/config)"
echo "macOS:  $(awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="macos" {c++} END {print c+0}' ~/.ssh/config)"
echo "VS Code: $(awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="vscode" {c++} END {print c+0}' ~/.ssh/config)"
```

---

## ⚡ Config Directives Explained

| Directive | Your Value | Purpose |
|-----------|-----------|---------|
| `ControlMaster` | `auto` | Reuse existing connections |
| `ControlPath` | `~/.ssh/master-%r@%h:%p` | Where master sockets are stored |
| `ControlPersist` | `yes` | Keep master in background |
| `ForwardAgent` | `no` | Don't expose keys to remote hosts |
| `AddKeysToAgent` | `yes` | Auto-add keys on first use |
| `IdentitiesOnly` | `yes` | Only try specified keys |
| `PreferredAuthentications` | `publickey` | Key-only auth |
| `RequestTTY` | `yes` (default) / `no` (vscode) | Request a TTY for shell |
| `RemoteCommand` | Varies by tag | Auto-run on connect |

---

## 🧩 Common Patterns to Extend

### Grouping by subnet

```bash
# All 192.168.0.x hosts
Match host "192.168.0.*"
  # No special config needed unless overriding
```

### Environment-specific config files

```bash
# Include other config files
# (add to ~/.ssh/config)
Include ~/.ssh/config.d/home
Include ~/.ssh/config.d/work
```

### Host grouping with wildcards

```bash
# All VMs
Host *.local *.vm
  # Already covered by individual definitions

# All VSCode remote hosts
Host vscode-*
  Tag vscode
  # Already covered by Match tagged
```
