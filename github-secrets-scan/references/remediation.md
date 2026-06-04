# 🧹 Remediation Guide — Removing Secrets from Git History

## When you find a leak

**Stop. Don't force-push until you've read the correct approach below.**

## If the secret is in the current file content

```bash
# 1. Replace the hardcoded value with an environment variable
# 2. Add the file to .gitignore if it's a .env or config file
# 3. Commit the fix
git add .
git commit -m "fix: remove hardcoded credentials, use env vars"

# 4. Push
git push

# 5. Rotate the leaked credential immediately
```

## If the secret is in git history (committed in the past)

### Option A: git-filter-repo (recommended)

```bash
# Install
brew install git-filter-repo

# Remove a specific file from all history
git filter-repo --path config/credentials.json --invert-paths

# Remove a file that was renamed
git filter-repo --path-glob '*.env' --invert-paths

# Replace a string across all history (use with extreme caution)
git filter-repo --replace-text <(echo 'ghp_LEAKED_TOKEN==>ghp_REDACTED')

# After filtering, force push
git remote add origin <url>
git push origin --force --all
```

### Option B: git filter-branch (built-in, slower)

```bash
# Remove a specific file from all branches
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/leaked_file" \
  --prune-empty --tag-name-filter cat -- --all

# Force push after
git push origin --force --all
git push origin --force --tags
```

### Option C: BFG Repo-Cleaner (Java, fast for large repos)

```bash
# Install: brew install bfg
# Remove all files matching a pattern
bfg --delete-files "*.env" .

# Replace text in all files
bfg --replace-text passwords.txt .

# Then cleanup
git reflog expire --expire=now --all && git gc --prune=now --aggressive
git push origin --force --all
```

## After removal

### 1. Rotate the credential

| Credential | Rotation Action |
|------------|----------------|
| GitHub token | https://github.com/settings/tokens → Regenerate |
| AWS key | AWS IAM Console → Deactivate + create new |
| OpenAI key | OpenAI Dashboard → Revoke + create new |
| Database password | ALTER USER / ALTER ROLE with new password |
| SSH key | Generate new key pair, update authorized_keys |
| Email/personal data | Can't rotate — just remove from history |

### 2. Notify collaborators

If the repo has other collaborators or is a fork:

```
⚠️ A credential was exposed in this repository's history.
Please consider any tokens/keys compromised and rotate them.
The history has been rewritten — all contributors should re-clone.
```

### 3. For GitHub-hosted repos

GitHub offers free secret scanning for public repos:

- Go to https://github.com/settings/security_analysis
- Enable "Secret scanning" for your repos
- GitHub will automatically detect known token formats and alert you

Alternatively, use GitHub's API to check for alerts:

```bash
gh api repos/:owner/:repo/secret-scanning/alerts
```

### 4. Clean up local clones

```bash
# After history rewrite, tell all collaborators to:
git fetch --all
git reset --hard origin/main  # or origin/master

# Or better: re-clone
cd .. && rm -rf repo && git clone <url>
```

## Prevention (do this now)

### Add a pre-commit hook

```bash
# Create .git/hooks/pre-commit in each repo:
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/sh
# Prevent committing sensitive data
git diff --cached | grep -E \
  '(ghp_|gho_|ghu_|ghs_|ghr_|AKIA|sk-[A-Za-z0-9]|-----BEGIN)' && \
  echo "⚠️  Possible secret detected! Aborting commit." && exit 1
exit 0
EOF
chmod +x .git/hooks/pre-commit
```

### Install gitleaks (recommended)

```bash
brew install gitleaks

# Run scan before each push
gitleaks detect --source . --verbose

# Or scan all history
gitleaks detect --source . --no-git

# Pre-commit hook with gitleaks
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/sh
gitleaks protect --staged --verbose 2>/dev/null
EOF
chmod +x .git/hooks/pre-commit
```

### .gitignore checklist

Ensure these are in every repo's `.gitignore`:

```
.env
.env.*
*.pem
*.key
*-key.pem
credentials*
secrets*
config/credentials*
*.cred
```

## If you accidentally leaked a GitHub token

1. **Revoke immediately**: https://github.com/settings/tokens
2. **Check for unauthorized access**: Check your repo's Settings → Security log
3. **Force push to remove from history** (but the token was already exposed)
4. **The token was valid between the commit and the revocation** — GitHub may have detected it and sent you an email

## Email addresses in git history

Your own email in commit history (from `git config user.email`) is generally not a leak — it's public information visible to anyone who clones the repo. However:

- **To change future commits**: `git config user.email "new@email.com"`
- **To rewrite past commits**: Use `git filter-repo --email-callback 'return b"new@email.com"'`

---

## TL;DR — Quick Decision Tree

```
Found a leak?
├─ In current file content (not in history)
│  ├─ Replace with env var
│  └─ Rotate credential
│
├─ In git history (committed and pushed)
│  ├─ Is it a credential/token/key?
│  │  ├─ git-filter-repo to remove from history
│  │  ├─ Force push
│  │  ├─ Rotate credential
│  │  └─ Notify collaborators
│  │
│  └─ Is it a personal email?
│     └─ INFO only — no action needed (it's public anyway)
│
└─ In a fork repo (you don't own the upstream)
   └─ INFO only — part of upstream codebase, not your leak
```
