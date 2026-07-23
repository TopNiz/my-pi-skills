---
name: pi-tmux
description: Start or resume an interactive Pi coding-agent session in a named tmux session on any SSH-configured machine. Use when the user wants Pi running remotely and persistently in a specific workspace, including VPN-specific SSH aliases.
---

# Remote Pi in tmux

Use this workflow to run **interactive Pi** in a detached, persistent tmux session on a remote machine. The SSH host alias determines the route; it can be a normal LAN alias or a VPN-specific alias. Do not special-case VPN networking.

## Required input

Get these from the user, asking only for anything ambiguous:

1. **SSH alias** — an alias from `~/.ssh/config`, for example `silicon-nizar-1.local` or `silicon-nizar-1-vpn.local`.
2. **Workspace** — either an absolute remote path or a registered workspace alias (see [Workspace aliases](#workspace-aliases)).
3. Optionally, a preferred tmux session name. Otherwise use `pi-<workspace-alias-or-basename>`.

Never scan networks to find a host unless the user specifically asks. An SSH alias is sufficient for any connection path.

## 1. Resolve and validate the SSH alias

Read the **entire** `~/.ssh/config`; `User`, `IdentityFile`, and other settings may come from the final `Host *` block. Confirm the alias exists and inspect its effective target without exposing private key material:

```bash
ssh -G <ssh-alias> | grep -E '^(hostname|user|port|tag|remotecommand)'
```

For automation, bypass any configured interactive `RemoteCommand` and TTY requirement:

```bash
ssh -o RemoteCommand=none -o RequestTTY=no -o ConnectTimeout=8 <ssh-alias> 'hostname'
```

If this fails, report the failure and do not create a local tmux session as a substitute.

## 2. Resolve the remote workspace

### Absolute path

Validate it remotely:

```bash
ssh -o RemoteCommand=none -o RequestTTY=no <ssh-alias> \
  'test -d "<remote-workspace-path>" && printf "workspace=%s\\n" "<remote-workspace-path>"'
```

Use a shell-safe quoted path when it is supplied by the user. If it does not exist, ask before choosing a different directory.

### Workspace aliases

Prefer a small per-machine registry at `~/.config/pi-tmux/workspaces`. Each non-comment line is a tab-separated pair:

```text
# alias<TAB>absolute remote path
git	/Users/nizarayed/MyDocuments/002-git
notes	/Users/nizarayed/MyDocuments/notes
```

Resolve an alias remotely. Store absolute paths in the registry; this keeps resolution shell-independent:

```bash
ssh -o RemoteCommand=none -o RequestTTY=no <ssh-alias> \
  'awk -F "\t" '\''$1 == "git" { print $2; exit }'\'' "$HOME/.config/pi-tmux/workspaces"'
```

Validate the resolved directory before using it. If the registry is absent or the requested alias is not found, ask the user for the path; do not silently create registry entries. Offer to add a confirmed path to the registry for future use.

## 3. Discover remote commands

Do not assume `tmux` or `pi` is on the non-interactive SSH `PATH`. First check a login shell:

```bash
ssh -o RemoteCommand=none -o RequestTTY=no <ssh-alias> \
  "zsh -lic 'command -v pi; command -v tmux'"
```

If `zsh` is unavailable, repeat with `bash -lic`. Use the discovered absolute tmux path if one is printed; otherwise use `tmux` from the login shell. If Pi is missing, tell the user rather than installing it without approval.

## 4. Create or resume the tmux session

Run tmux **on the remote machine**, detached, with its starting directory set to the resolved workspace. Start Pi through a login interactive shell so version-manager paths and user configuration load.

Example for session `pi-git` and a resolved remote workspace:

```bash
ssh -o RemoteCommand=none -o RequestTTY=no <ssh-alias> \
  'zsh -lic '\''
    workspace="<remote-workspace-path>"
    session="pi-git"
    if /opt/homebrew/bin/tmux has-session -t "$session" 2>/dev/null; then
      echo "tmux session already exists: $session"
    else
      /opt/homebrew/bin/tmux new-session -d -s "$session" -c "$workspace" '\''\''\''exec zsh -lic "exec pi"'\''\''\''
      echo "Created tmux session: $session"
    fi
  '\'''
```

Adapt the shell and tmux path based on discovery. Prefer `has-session` before `new-session`: never kill, replace, or inject input into an existing session unless the user explicitly requests it.

When quoting becomes complex, send a small script over SSH (for example, Base64-encoded) rather than interpolating untrusted user values into shell code.

## 5. Verify Pi and provide the attach command

Inspect the remote tmux pane without disrupting it:

```bash
ssh -o RemoteCommand=none -o RequestTTY=no <ssh-alias> \
  '<tmux-path> capture-pane -p -J -t <session>:0.0 -S -30'
```

Confirm the output shows Pi’s startup screen and the expected workspace. Then give the user the interactive attach command:

```bash
ssh -t <ssh-alias> 'tmux attach -t <session>'
```

If the SSH config’s normal `RemoteCommand` already starts tmux, keep the explicit `tmux attach` command; it is unambiguous and works consistently across aliases.

## Safety and session conventions

- Use SSH aliases exactly as configured; VPN aliases are simply separate aliases pointing to alternate addresses.
- Use a stable, descriptive tmux name: `pi-<workspace-alias>` is preferred.
- Keep Pi interactive: do **not** use `pi -p`, `--mode json`, or `--mode rpc` for this task.
- Create sessions detached, then attach only when requested.
- Do not expose SSH keys, credentials, or full private configuration in responses.
- Before a first remote Pi session, verify that Pi may prompt for project trust; leave that decision to the user in the attached interactive session.
