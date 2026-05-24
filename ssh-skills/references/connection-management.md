# Connection Management

Mastering SSH connections — multiplexing, tunneling, and everything between.

---

## 🔄 ControlMaster Multiplexing

Your config has `ControlMaster auto` with `ControlPersist yes`. This is the **single most impactful SSH optimization**.

### How it works

```
First connection:
  ┌─────────┐     TCP handshake     ┌──────────┐
  │  Client  │ ──────────────────▶  │  Server  │
  │          │ ◀──────────────────  │          │
  └─────────┘     Auth + session    └──────────┘
       │
       ▼ Creates ~/.ssh/master-user@host:22

Second+ connections (instant):
  ┌─────────┐    reuse socket       ┌──────────┐
  │  Client  │ ──────────────────▶  │  Server  │
  │          │     (no TCP!)        │          │
  └─────────┘                       └──────────┘
```

### Managing master sockets

```bash
# List all active sockets
ls -l ~/.ssh/master-*

# Check if a host has an active master connection
ssh -O check <host-alias>
# Output: Master running (pid=12345)

# Close the master connection gracefully
ssh -O stop <host-alias>

# Close all master connections
for sock in ~/.ssh/master-*; do
  host=$(echo "$sock" | sed 's/.*master-//' | sed 's/@.*//')
  echo "Stopping master for $host"
  ssh -O stop "$host" 2>/dev/null || true
done
```

### When to bypass the master

```bash
# Force new connection (bypass multiplexing)
ssh -S none <host-alias>

# Use a different control path (separate socket)
ssh -o ControlPath=/tmp/ssh-%r@%h:%p <host-alias>
```

---

## 🚇 Port Forwarding / Tunneling

### Local Forwarding — Expose remote services locally

```bash
# Syntax: ssh -L local_port:target_host:target_port <jump-host>
#                               ↳ "localhost" means relative to jump-host

# Example: Remote web server on port 80 → local port 8080
ssh -L 8080:localhost:80 <remote-server-1>
# Now visit http://localhost:8080

# Example: Remote database (not exposed to internet)
ssh -L 3306:localhost:3306 <ubuntu-server>
# Now connect: mysql -h 127.0.0.1 -P 3306 -u user -p

# Multiple tunnels at once
ssh -L 8080:localhost:80 -L 8443:localhost:443 <remote-server-1>
```

### Remote Forwarding — Expose local services remotely

```bash
# Syntax: ssh -R remote_port:local_host:local_port <gateway>
# Makes YOUR local service available on the REMOTE machine

# Example: Expose your local dev server (port 3000) on remote port 9000
ssh -R 9000:localhost:3000 <vm-fedora>
# On <vm-fedora>, visit http://localhost:9000

# Useful for: sharing local previews, webhooks, APIs
```

### Dynamic Forwarding — SOCKS Proxy

```bash
# Create a SOCKS5 proxy through the remote server
ssh -D 1080 <remote-server-1>

# Configure your browser/app:
#   Proxy type: SOCKS5
#   Host: localhost
#   Port: 1080
#   DNS: remote (proxy DNS through tunnel)

# Test with curl:
curl --socks5-hostname localhost:1080 https://ifconfig.me
# → Shows the remote server's IP
```

### Persistent tunnels with autossh

```bash
# autossh automatically reconnects if tunnel drops
# Install: brew install autossh (macOS) / apt install autossh (Linux)

autossh -M 0 -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" \
  -L 8080:localhost:80 \
  -N <remote-server-1>
```

---

## 🏃 Keep Alive — Stop Disconnections

```bash
# Prevent SSH from timing out during long sessions
ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=3 <host-alias>

# To make permanent, add to ~/.ssh/config under Host *:
# ServerAliveInterval 30
# ServerAliveCountMax 3
```

---

## 🌉 Jump Host / Bastion

```bash
# Connect to internal host through a bastion
ssh -J <bastion-host> <internal-host>

# Multiple jumps
ssh -J <bastion-1>,<bastion-2> <internal-host>

# For permanent use, add to ~/.ssh/config:
# Host <internal-host>
#   ProxyJump <bastion-host>
```

---

## 📡 Debugging Connections

```bash
# Verbose (v1-3) — useful for auth issues
ssh -v <host-alias>       # Basic info
ssh -vv <host-alias>      # More detail
ssh -vvv <host-alias>     # Everything (debug level)

# Test if a host is reachable (quick)
ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no \
  -o BatchMode=yes <host-alias> "echo OK" 2>/dev/null || echo "FAIL"

# Show effective config for a host
ssh -G <host-alias> | grep -E "hostname|user|port|identityfile|forwardagent"
```

---

## 📊 Connection Performance

```bash
# Benchmark first vs subsequent connections
time ssh <remote-server-1> "exit"

# Measure raw SSH handshake time (no multiplexing)
time ssh -S none <remote-server-1> "exit"

# Expected: 0.5-2s for first, 0.05-0.2s for subsequent (with ControlMaster)
```
