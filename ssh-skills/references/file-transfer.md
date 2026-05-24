# File Transfer

SCP and RSYNC patterns for every scenario in your infrastructure.

---

## 📤 SCP — Secure Copy (Simple)

### Push (local → remote)

```bash
# Single file
scp ./local-file.txt <host-alias>:/remote/path/

# With different remote filename
scp ./local-file.txt <host-alias>:/remote/path/newname.txt

# Directory recursively
scp -r ./project/ <host-alias>:/remote/path/

# With compression (slower CPU, faster network)
scp -C ./large-file.tar.gz <host-alias>:~/

# Preserve timestamps and permissions
scp -p ./important.conf <host-alias>:~/

# Limit bandwidth (KB/s) — useful for not saturating links
scp -l 1000 ./large-file.iso <host-alias>:~/
```

### Pull (remote → local)

```bash
# Single file
scp <host-alias>:/remote/file.txt ./local/

# Directory
scp -r <host-alias>:/remote/dir/ ./local/

# Multiple files from same remote
scp <host-alias>:/remote/{file1,file2,file3}.txt ./local/
```

### Through a jump host

```bash
# Using ProxyJump (-J)
scp -J <jump-host> <jump-host>:<file> ./local/

# Using -o ProxyJump (same thing)
scp -o ProxyJump=<jump-host> ./local-file.txt <internal-host>:/remote/
```

### Examples from your infrastructure

```bash
# Deploy a script to remote server
scp ./deploy.sh <remote-server-1>:/usr/local/bin/

# Pull logs from Ubuntu server
scp <ubuntu-server>:/var/log/syslog ./logs/syslog-$(date +%Y%m%d)

# Copy config to all VMs
for host in <vm-fedora> <vm-ubuntu>; do
  scp ./app.conf "$host":/etc/my-app/
done

# Backup from Mac
scp <mac-silicon>:~/Documents/important.docx ~/Backups/
```

---

## 🔄 RSYNC — Efficient, Resumable Transfers

### Why rsync over scp?

| Feature | SCP | RSYNC |
|---------|-----|-------|
| Partial transfer resume | ❌ | ✅ |
| Only sends diffs | ❌ | ✅ |
| Compression | Single flag `-C` | Built-in `-z` |
| Exclude patterns | ❌ | ✅ |
| Delete files | ❌ | ✅ |
| Dry-run | ❌ | ✅ |
| Progress display | ❌ | ✅ |

### Basic patterns

```bash
# Archive mode (recursive, preserves permissions/times/owner)
rsync -avz ./local-dir/ <host-alias>:/remote-dir/

# Note: trailing slash on source means "copy contents of dir"
# No trailing slash means "copy the dir itself"
rsync -avz ./local-dir <host-alias>:/remote-dir/
# → creates /remote-dir/local-dir/

rsync -avz ./local-dir/ <host-alias>:/remote-dir/
# → copies contents into /remote-dir/
```

### Advanced patterns

```bash
# Dry-run (safety first!)
rsync -avz --dry-run ./project/ <host-alias>:/backups/project/

# Show progress
rsync -avz --progress ./large-data/ <host-alias>:/data/

# Delete files on destination not in source (mirror)
rsync -avz --delete ./source/ <host-alias>:/destination/

# Exclude patterns
rsync -avz --exclude='.git/' --exclude='node_modules/' \
  --exclude='*.log' --exclude='.DS_Store' \
  ./project/ <host-alias>:/project/

# Include specific patterns while excluding everything else
rsync -avz --include='*.py' --include='*.conf' --exclude='*' \
  ./src/ <host-alias>:/src/

# Bandwidth limit (KB/s)
rsync -avz --bwlimit=500 ./large/ <host-alias>:/data/

# Remote shell options (e.g., different port)
rsync -avz -e 'ssh -p 2222' ./dir/ <host-alias>:/dir/
```

### Backup scenarios

```bash
# Incremental backup with timestamp
rsync -avz --link-dest=../backup-yesterday \
  ./data/ <host-alias>:~/backups/backup-today/

# Full system backup (exclude pseudo-filesystems)
rsync -avz --exclude={/dev/,/proc/,/sys/,/tmp/,/run/,/mnt/,/media/} \
  / <host-alias>:~/backups/$(hostname)-$(date +%Y%m%d)/
```

### Sync from all tagged hosts

```bash
# Pull logs from all Linux hosts
for host in $(awk '/^Host /{h=\$2} \$1=="Tag" && \$2=="linux" {print h}' ~/.ssh/config); do
  rsync -avz "$host":/var/log/syslog "./logs/$host-syslog-$(date +%Y%m%d)"
done
```

---

## 📁 Advanced File Operations

### tar + SSH (no temp files)

```bash
# Compress on-the-fly and send
tar czf - ./project/ | ssh <host-alias> "tar xzf - -C /remote/path/"

# Pull and decompress
ssh <host-alias> "tar czf - /remote/data/" | tar xzf - -C ./local/

# With encryption
tar czf - ./secret/ | openssl enc -aes-256-cbc -salt | \
  ssh <host-alias> "cat > /secure/backup.tar.gz.enc"
```

### Verify file integrity after transfer

```bash
# Compare checksums
scp ./file.zip <host-alias>:/tmp/
echo "Local:  $(md5sum ./file.zip | cut -d' ' -f1)"
echo "Remote: $(ssh <host-alias> "md5sum /tmp/file.zip | cut -d' ' -f1")"

# Quick hash comparison
local_hash=$(md5sum ./file.zip | awk '{print $1}')
remote_hash=$(ssh <host-alias> "md5sum /tmp/file.zip" | awk '{print $1}')
[ "$local_hash" = "$remote_hash" ] && echo "✅ Match" || echo "❌ Mismatch"
```

### Diff remote vs local file

```bash
# Check if files differ
ssh <host-alias> "cat /remote/config.yml" | diff - ./local/config.yml

# Rsync dry-run already does this:
rsync -avz --dry-run --itemize-changes ./local/ <host-alias>:/remote/
```

---

## 🎯 Use-Case Quick Reference

| Task | Command |
|------|---------|
| Quick single file push | `scp ./file <host>:/path/` |
| Quick single file pull | `scp <host>:/file ./` |
| Directory push | `scp -r ./dir/ <host>:/path/` |
| Efficient sync | `rsync -avz ./dir/ <host>:/path/` |
| Mirror (delete extras) | `rsync -avz --delete ./dir/ <host>:/path/` |
| Dry-run to preview | `rsync -avz --dry-run ./dir/ <host>:/path/` |
| Transfer via jump host | `scp -J <jump> ./file <host>:/path/` |
| Compress on slow links | `scp -C` or `rsync -z` |
| Resumed/partial transfer | `rsync --partial` (default) |
| Bandwidth limited | `rsync --bwlimit=500` or `scp -l 500` |
