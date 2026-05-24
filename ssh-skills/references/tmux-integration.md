# TMUX Integration

Working with the tmux sessions that auto-attach when you SSH into tagged hosts.

---

## 🎯 How It Works

When you SSH into a host with `Tag linux` or `Tag macos`, the `RemoteCommand` automatically attaches to (or creates) a tmux session named `ssh_tmux`:

```
$ ssh <remote-server-1>
  ┌─────────────────────────────────────────┐
  │  RemoteCommand fires:                   │
  │  tmux -u new -A -s ssh_tmux             │
  │         │        │                      │
  │         │        └── session name       │
  │         └────────────────── attach or   │
  │                            create (-A)  │
  └─────────────────────────────────────────┘
```

This means:
- **First connection**: Creates a new tmux session
- **Subsequent connections**: Attach to the existing session (you resume where you left off)
- **Detach**: Session keeps running (disconnect safely, reconnect later)

---

## ⌨️ Essential Tmux Keybindings

### Session management

| Keystroke | Action |
|-----------|--------|
| `Ctrl+B d` | Detach from session (SSH disconnects) |
| `Ctrl+B s` | List/switch sessions |
| `Ctrl+B $` | Rename current session |
| `Ctrl+B w` | List all windows in a tree |

### Window management

| Keystroke | Action |
|-----------|--------|
| `Ctrl+B c` | Create new window |
| `Ctrl+B ,` | Rename current window |
| `Ctrl+B &` | Kill current window |
| `Ctrl+B n` | Next window |
| `Ctrl+B p` | Previous window |
| `Ctrl+B 0-9` | Go to window by number |
| `Ctrl+B f` | Find window by name |
| `Ctrl+B l` | Go to last active window |

### Pane management

| Keystroke | Action |
|-----------|--------|
| `Ctrl+B %` | Split pane vertically |
| `Ctrl+B "` | Split pane horizontally |
| `Ctrl+B o` | Cycle through panes |
| `Ctrl+B ←↑→↓` | Navigate to pane |
| `Ctrl+B z` | Zoom/unzoom current pane |
| `Ctrl+B x` | Kill current pane |
| `Ctrl+B {` | Swap pane left |
| `Ctrl+B }` | Swap pane right |
| `Ctrl+B space` | Cycle pane layouts |

### Copy mode

| Keystroke | Action |
|-----------|--------|
| `Ctrl+B [` | Enter copy mode |
| `Space` | Start selection |
| `Enter` | Copy selection |
| `Ctrl+B ]` | Paste copied text |

---

## 🪟 Advanced TMUX Workflows

### Multiple sessions

```bash
# Your SSH config auto-attaches to "ssh_tmux"
# To create additional sessions manually on the remote:

# After connecting, create a new session:
tmux new -s work-session

# List sessions:
tmux ls

# Switch sessions from inside tmux:
# Ctrl+B s → choose with arrows, Enter

# Attach to a specific session:
tmux attach -t work-session
```

### Nested tmux (tmux inside tmux)

```bash
# If you SSH from a host that also has tmux, you get "nested" tmux
# Press Ctrl+B twice to send command to inner tmux:
# Ctrl+B, Ctrl+B c   → new window in inner tmux

# Better approach: disable tmux at one level
# On the outer machine, detach first, then SSH
# Or use a different session name for inner sessions
```

---

## 🛠️ TMUX Customizations for Your Setup

### Session naming convention

You could create script to manage named sessions:

```bash
# Create or attach to a project-specific session
tmux-project() {
  local session_name="${1:-$(basename "$PWD")}"
  tmux new -A -s "$session_name"
}

# Usage: tmux-project myproject
```

### Auto-rename windows based on command

```bash
# Add to remote ~/.tmux.conf:
set-option -g allow-rename on
set-option -g automatic-rename on

# Or disable if you prefer manual naming:
set-option -g allow-rename off
```

### Health monitoring in status bar

```bash
# Add to remote ~/.tmux.conf:
set -g status-right '#[fg=green]#(uptime | cut -d, -f2-) #[default]'
set -g status-left '#[fg=cyan]#S #[default]'
```

---

## 🔌 TMUX + VS Code

Your VS Code hosts (`vscode-*`) explicitly disable tmux via `RequestTTY no` and `RemoteCommand none`. This is correct because VS Code's Remote SSH extension manages its own terminal sessions.

If you need both:
- Use `<host-alias>` when you want tmux (terminal)
- Use `vscode-<host-alias>` when you want VS Code (no tmux)

---

## 📋 Useful TMUX Commands (Run on Remote)

```bash
# Run these INSIDE an SSH session (or via ssh cmd)

# List all sessions
tmux list-sessions

# Kill a session
tmux kill-session -t ssh_tmux

# Rename session
tmux rename-session -t ssh_tmux my-project

# Create new window in existing session
tmux new-window -t ssh_tmux -n "monitoring" "htop"

# Split current window in existing session
tmux split-window -t ssh_tmux -h "journalctl -f"

# Send command to a specific pane
tmux send-keys -t ssh_tmux:0.0 "htop" Enter

# Capture pane content to file
tmux capture-pane -t ssh_tmux:0.0 -p > /tmp/pane-output.txt
```

---

## ⚡ Automation: TMUX from Local

```bash
# Run command in a tmux window on the remote WITHOUT attaching
ssh <host-alias> "tmux new-window -t ssh_tmux -n 'htop' 'htop'"

# Check if tmux is running on remote
ssh <host-alias> "tmux list-sessions" 2>/dev/null || echo "No tmux sessions"

# Send keystrokes to a running tmux session
ssh <host-alias> "tmux send-keys -t ssh_tmux:0 'echo hello' Enter"

# Capture output from a tmux session
ssh <host-alias> "tmux capture-pane -t ssh_tmux:0 -p"
```

---

## 🔄 Disabling TMUX Temporarily

```bash
# If you need a plain shell without tmux for one session:
ssh -t <host-alias> "bash --norc"

# Or override the RemoteCommand:
ssh -o RemoteCommand=none <host-alias>

# Or bypass config entirely:
ssh -F /dev/null <user>@<ip-address>
```
