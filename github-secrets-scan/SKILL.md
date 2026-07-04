---
name: github-secrets-scan
description: Scan your GitHub public repositories for leaked sensitive data — passwords, API keys, tokens, SSH keys, emails, phone numbers, connection strings, and more. Scans both code files and full git commit history.
allowed-tools: read write edit bash
---

# 🔒 GitHub Secrets Scanner

Scan your **public** GitHub repositories for accidentally committed sensitive data. Supports all your GitHub accounts (TopNiz, dotit-bot).

---

## 🚀 Quick Start

```bash
cd ~/.agents/skills/github-secrets-scan
python3 scripts/scan.py
```

---

## 📋 What Gets Scanned

### Sensitive Data Patterns

| Category | What's detected |
|----------|----------------|
| 🔑 **Credentials** | passwords, passwd, pwd in code |
| 🔐 **API Keys** | AWS (AKIA...), OpenAI (sk-...), Google (AIza...), generic API keys/secrets |
| 🎫 **Tokens** | GitHub tokens (ghp_/gho_/ghu_/ghs_/ghr_), GitHub PATs, JWT tokens, Bearer tokens |
| 🔏 **Private Keys** | RSA/DSA/EC/OpenSSH/PGP private keys embedded in code or commits |
| 🔌 **Connection Strings** | postgresql://, mysql://, mongodb://, redis://, amqp:// with embedded passwords |
| 📧 **Emails** | Real email addresses (filters out example.com, test@, npm package.json authors) |
| 📞 **Phone Numbers** | Tunisian (+216), French (+33), and international numbers |
| 🌐 **Internal URLs** | localhost, 10.x.x.x, 192.168.x.x, 172.x.x.x |
| 🪪 **SSH Keys** | ssh-rsa, ssh-ed25519 public keys embedded in code |
| 🔍 **OAuth** | Slack tokens (xox[baprs]-), generic Bearer tokens |

### Scan Scope

For **each public repository**, the scanner checks:

1. **Code files** — all tracked files in the latest commit (excludes .git, node_modules, __pycache__, dist/, build/)
2. **Git commit history** — full `git log --all -p` for secrets that were committed then later removed

---

## 🗺️ Workflow

### 1. List public repositories

Uses `gh` CLI (already authenticated with your 3 accounts) to list **only public** repos:

```bash
# The script does this automatically:
#   gh repo list --limit 200 --json name,visibility,owner
# It filters to only PUBLIC repos and respects visibility
```

Your public repos automatically detected:
- **TopNiz**: 34 public repos
- **dotit-bot**: 1 public repo (dotit-bot)

### 2. Shallow clone + scan

```bash
python3 scripts/scan.py [options]
```

Options:
```bash
# Scan all accounts (default)
python3 scripts/scan.py

# Scan specific repos only
python3 scripts/scan.py --repos TopNiz/finperso TopNiz/nono_rent_backend

# Skip commit history scan (faster)
python3 scripts/scan.py --no-commits

# Skip file content scan
python3 scripts/scan.py --no-files

# Only scan a specific pattern category
python3 scripts/scan.py --only credentials tokens

# Output to file for review
python3 scripts/scan.py -o /tmp/scan_results.json

# JSON output (for programmatic use)
python3 scripts/scan.py --json

# Exclude fork repos (upstream codebases you don't control)
python3 scripts/scan.py --no-forks

# Limit depth of shallow clone (default: 50 commits)
python3 scripts/scan.py --depth 100

# Skip specific repos
python3 scripts/scan.py --skip TopNiz/rabbitmq-server TopNiz/arduino-esp32

# Scan + AI classification (filters test/example findings)
python3 scripts/scan.py --ai-classify

# Scan + interactive mitigation (mark findings as normal/resolved)
python3 scripts/scan.py --mitigate

# Scan + AI + auto-store into mitigation DB
python3 scripts/scan.py --ai-classify

# Manage the mitigation database (list, remove, stats, vacuum)
python3 scripts/scan.py --manage-mitigations

# Use a custom mitigation DB path
python3 scripts/scan.py --mitigation-db /path/to/custom.db

# Reset all repo scan preferences — rediscover all repos
python3 scripts/scan.py --repos-reset
```

### 3. AI Classification (optional)

After scanning, run AI classification on the findings to automatically identify
normal/test data vs. real secrets:

```bash
# One-step: scan + classify
python3 scripts/scan.py --ai-classify

# Or run classification on a previous scan result
python3 scripts/ai_classify.py reports/github-secrets-scan_2026-06-10_06-00-02.json
```

The AI classifier uses pi with **OpenAI Codex (GPT-5.4 mini)** to analyze each
finding. It adds an `ai_verdict` field (`"normal"` or `"review"`) and a reason.

Results are saved to a `_classified.json` file alongside the original report.

### 4. Repo Scan Preferences

The mitigation database tracks which repos to scan. The workflow is:

1. **First encounter:** New repos are **automatically scanned** and stored in
   the DB with `to_be_scanned = 1`. No prompting.
2. **Report flags them:** The scan report highlights newly discovered repos
   in a dedicated `🆕 NEWLY DISCOVERED REPOS` section, showing which ones had
   findings and which were clean.
3. **You decide later:** After reviewing the report, tell me to flag specific
   repos as skipped. I'll update the DB.

This works for automation (cron) and manual runs alike — no interactive
prompts needed. You review the output and decide what to skip.

```bash
# Reset all preferences — will re-discover all repos on next scan
python3 scripts/scan.py --repos-reset

# List all tracked repos and their flags
python3 scripts/mitigation_db.py repos

# Show only skipped repos
python3 scripts/mitigation_db.py repos --skipped

# Show only repos to be scanned
python3 scripts/mitigation_db.py repos --scanned
```

### 5. AI auto-stores normal findings into Mitigation Database

When using `--ai-classify`, the AI classifier **automatically stores** every
finding it classifies as "normal" into the mitigation database. Additionally,
before calling the AI, it checks the database first — if a finding was already
reviewed, it skips the AI call entirely. This saves tokens on repeated scans.

```bash
# First scan: AI classifies everything, stores "normal" findings
python3 scripts/scan.py --ai-classify

# Second scan: DB already has those — AI is only called on *new* findings
python3 scripts/scan.py --ai-classify

# DB-only mode: no AI at all, just use the database (fastest)
python3 scripts/ai_classify.py --db-only reports/scan_results.json
```

### 6. Interactive Mitigation Review (recommended)

After a scan, use `--mitigate` to review each finding one-by-one and
permanently mark it as **normal** (false positive / test data) or **resolved**
(remediated). Once marked, the finding is **silently skipped** on all future
scans — no more noise.

```bash
# Scan + interactive mitigation
python3 scripts/scan.py --mitigate

# Scan, then review each finding with [n]ormal / [r]esolved / [s]kip / [q]uit
```

Each entry supports an optional comment for your future reference.

### 7. Manage the Mitigation Database

```bash
# List all entries
python3 scripts/mitigation_db.py list

# Filter by verdict
python3 scripts/mitigation_db.py list --verdict normal

# Filter by repo
python3 scripts/mitigation_db.py list --repo TopNiz/finperso

# Remove an entry by its fingerprint
python3 scripts/mitigation_db.py remove <fingerprint>

# Show statistics
python3 scripts/mitigation_db.py stats

# Shortcut: via scan.py
python3 scripts/scan.py --manage-mitigations
```

The database is a **SQLite** file at `scripts/mitigation.db`. It is
gitignored — your review decisions stay local.

### 8. Review results

The scanner categorizes findings by **severity**:

| Level | Color | Meaning |
|-------|-------|---------|
| 🔴 **CRITICAL** | Red | Live passwords, API keys, tokens, private keys, connection strings |
| 🟡 **HIGH** | Yellow | Bearer tokens, JWT, SSH keys, `api_key=` / `secret=` assignments |
| 🔵 **MEDIUM** | Blue | Real emails (other people's), phone numbers, internal IPs/hostnames |
| ⚪ **INFO** | Gray | localhost refs, your own git email, npm maintainer emails |
| ✅ **CLEAN** | Green | No findings |

---

## 📊 Result Format

```
┌─────────────────────────────────────────────────────┐
│ 🔒 GitHub Secrets Scan Report                       │
│ Scanned: 2026-06-04T14:30:00Z                       │
│ Account: TopNiz                                     │
│ Repos scanned: 12 / 34 public                       │
└─────────────────────────────────────────────────────┘

🔴 CRITICAL (2 findings)
  ───────────────────────────────────────────
  📁 TopNiz/nono_rent_backend
    📄 src/config.py (line 42)
    → DB_PASSWORD = "postgres"          ⚠️ Hardcoded DB password
    
    📄 .env.example (line 5)
    → GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx  🚫 Token pattern in code

🟡 HIGH (5 findings)
  ───────────────────────────────────────────
  📁 TopNiz/finperso (commit history)
    → User email: nizar.ayed@tourisfair.de (in 8 commits)
  
  📁 TopNiz/nono_rent_backend (commit history)
    → Other email: user@example.com (test data)
    → Other email: user2@example.com (test data)

🔵 MEDIUM (3 findings)
  ───────────────────────────────────────────
  📁 TopNiz/my-lazy-nvim (commit history)
    → Old email: nizarayed@plania.io
  
  📁 TopNiz/gemini-cli (fork - file content)
    → Placeholder private key in tests/

⚪ INFO (8 findings)
  ───────────────────────────────────────────
  📁 TopNiz/nono_rent_backend
    → App emails: admin@nono-rent.fr, landlord@nono-rent.fr
    → Used in test fixtures — review if real emails needed

✅ CLEAN repos (7)
  ───────────────────────────────────────────
  • bf_niz, ls-view, meoblog, prototype-js
  • deep-dive-javascript, w-engine
  • tourisfair_sampleApp
```

---

## 🧹 Remediation Actions

When sensitive data is found, offer the user these actions:

### For secrets in current code (file content)

```bash
# 1. Remove the secret from code
# 2. Add .env to .gitignore if not already there
# 3. Use environment variables or a secrets manager
# 4. Rotate the compromised credential
```

### For secrets in commit history (git leak)

```bash
# Option A: Use git filter-branch (simple, but rewrites history)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/file_containing_secret" \
  --prune-empty --tag-name-filter cat -- --all

# Option B: Use git-filter-repo (recommended, faster)
# Install: brew install git-filter-repo
git filter-repo --path path/to/leaked_file --invert-paths

# Option C: For GitHub, use GitHub's secret scanning alerts
# Go to: https://github.com/settings/security_analysis
```

### For leaked tokens/credentials

```bash
# GitHub tokens
gh auth refresh --invalidate-token
# → Regenerate at: https://github.com/settings/tokens

# AWS keys
# → Rotate at: https://console.aws.amazon.com/iam

# Generic passwords
# → Change immediately on the affected service
```

---

## ⚙️ Configuration

### Config file: `scripts/config.json`

```json
{
  "accounts": {
    "active": ["TopNiz", "dotit-bot"],
    "list": {
      "TopNiz": {
        "github_username": "TopNiz",
        "include_forks": true,
        "depth": 50,
        "exclude_repos": []
      },
      "dotit-bot": {
        "github_username": "dotit-bot",
        "include_forks": false,
        "depth": 50,
        "exclude_repos": []
      }
    }
  },
  "scan": {
    "max_file_size_kb": 500,
    "ignored_extensions": [".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
      ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".mp3", ".pdf", ".zip",
      ".gz", ".tar", ".bz2", ".xz", ".7z", ".rar", ".bin", ".exe",
      ".dll", ".so", ".dylib", ".o", ".a", ".lib", ".class", ".pyc",
      ".pyo", ".pyd", ".whl", ".egg", ".map", ".br", ".webp", ".avif"],
    "ignored_dirs": ["node_modules", "__pycache__", ".git", "dist", "build",
      ".next", ".nuxt", "vendor", ".bundle", "target", ".gradle", "coverage",
      ".nyc_output", ".tox", ".eggs"],
    "ignored_files": ["package-lock.json", "yarn.lock", "pnpm-lock.yaml",
      "Gemfile.lock", "Cargo.lock", "poetry.lock", "composer.lock",
      "uv.lock", "lazy-lock.json"],
    "ignored_file_glob": ["*.lock", "*.sum"],
    "max_findings_per_repo": 50,
    "work_dir": "/tmp/github-secrets-scan"
  }
}
```

### Pattern names reference (for `--only`)

Use these names with `--only` to scan only specific pattern categories:

```bash
python3 scripts/scan.py --only password_assignment private_key
python3 scripts/scan.py --only email_address
python3 scripts/scan.py --only generic_api_key bearer_token
```

| Pattern name | Severity | What it detects |
|-------------|----------|----------------|
| `password_assignment` | 🔴 critical | `password = "..."` or `passwd: ...` in code |
| `aws_access_key` | 🔴 critical | `AKIA...` (24-char AWS key IDs) |
| `aws_secret_key` | 🔴 critical | `AWS_SECRET_ACCESS_KEY = "..."` |
| `openai_api_key` | 🔴 critical | `sk-...` (OpenAI API keys) |
| `google_api_key` | 🔴 critical | `AIza...` (Google API keys) |
| `github_token` | 🔴 critical | `ghp_/gho_/ghu_/ghs_/ghr_...` tokens |
| `github_fine_grained_pat` | 🔴 critical | `github_pat_...` fine-grained PATs |
| `slack_token` | 🔴 critical | `xox[baprs]-...` Slack tokens |
| `private_key` | 🔴 critical | `-----BEGIN ... PRIVATE KEY-----` |
| `db_connection_string` | 🔴 critical | `postgresql://user:pass@host/` |
| `generic_api_key` | 🟡 high | `api_key = "..."` / `api_secret = "..."` |
| `jwt_token` | 🟡 high | `eyJ...` JWT tokens |
| `bearer_token` | 🟡 high | `Bearer ...` authorization headers |
| `ssh_public_key` | 🟡 high | `ssh-rsa AAA...` embedded keys |
| `url_credentials` | 🟡 high | `https://user:pass@host` |
| `email_address` | 🔵 medium | Real emails (`user@domain.com`) |
| `phone_tunisia` | 🔵 medium | +216 / 0X... Tunisian numbers |
| `phone_france` | 🔵 medium | +33 / 0X... French numbers |
| `phone_us` | 🔵 medium | US phone number format |
| `internal_ip` | 🔵 medium | 10.x.x.x, 192.168.x.x, 172.16-31.x.x |
| `internal_hostname` | 🔵 medium | `*.local`, `*.internal`, `*.corp` URLs |
| `localhost_reference` | ⚪ info | `http://localhost:PORT` usage |

---

## 🔬 Pattern Customization

The scanning regex patterns are defined in `references/patterns.md`. Each pattern has:

```yaml
- name: "pattern_name"
  description: "What this pattern detects"
  severity: "critical|high|medium|info"
  regex: "the regex pattern"
  context_lines: 0
  false_positive_rules:
    - "skip if filename matches *.test.js"
    - "skip if matched value contains 'example'"
```

To add a new pattern, edit `scripts/scan.py` (the `BUILTIN_PATTERNS` list) and also document it in `references/patterns.md`. The scanner uses the patterns defined in `scan.py` directly.

---

## 🧠 How It Works (Technical)

1. **Repository Discovery**: Uses `gh repo list` with JSON output, filters `visibility == "PUBLIC"`
2. **Repo Scan Preferences**: Each repo is checked against the mitigation DB. New repos prompt for your preference; skipped repos are excluded without cloning.
3. **Cloning**: Git shallow clone (`--depth N`) to minimize bandwidth — only the last N commits
4. **File Scan**: Walks all tracked files, reads text content, applies regex patterns
5. **Commit History Scan**: Runs `git log --all -p` and applies the same patterns to the unified diff output
6. **Mitigation DB Filter**: Every finding is checked against the DB. Already-reviewed findings are silently removed.
7. **False Positive Filtering**:
   - Skips binary files by extension
   - Skips known safe directories (node_modules, vendor, dist)
   - Ignores example.com, test@, placeholder values
   - Flags npm package.json maintainer emails as INFO only
   - Detects fork repos and flags upstream code separately
8. **Reporting**: Grouped by severity, with deduplication and sample output

---

## 📁 Skill Files

```
github-secrets-scan/
├── SKILL.md                      ← This file
├── scripts/
│   ├── config.json               ← Account & scan configuration
│   ├── scan.py                   ← Main scanner script
│   ├── ai_classify.py            ← AI classification (OpenAI Codex)
│   ├── mitigation_db.py          ← Mitigation database manager
│   ├── mitigation.db             ← SQLite DB (gitignored, auto-created)
│   └── .gitignore                ← Ignores *.db, reports/
├── references/
│   ├── patterns.md               ← All regex patterns with descriptions
│   └── remediation.md            ← Step-by-step cleanup guides
```

The mitigation database (`mitigation.db`) is SQLite and auto-created on first
use. It stores your review decisions and repo scan preferences locally.
It contains two tables:

| Table | Purpose |
|-------|---------|
| `mitigations` | Findings marked as normal (false positive) or resolved (remediated) — silently skipped on future scans |
| `repos` | Repo scan preferences — `to_be_scanned` flag set interactively per repo, persists across scans |

The database is excluded from git via `.gitignore`.

---

## 🔐 Security Notes

- **Only public repos are scanned** — private repos are explicitly filtered out by the script
- **No credentials stored** — uses `gh` CLI (already authenticated via macOS keychain) — never stores or outputs your GitHub tokens
- **Scan output contains findings** — handle with care, don't commit scan results to git
- **Fork repos** (gemini-cli, rabbitmq-server, etc.) may contain placeholder/test secrets from upstream projects — these are flagged separately
- **Your own email** in commit history is expected (git config) — flagged as INFO

---

## ⚡ Quick Scan Examples

```bash
# Full scan of all public repos (may take a while)
cd ~/.agents/skills/github-secrets-scan && python3 scripts/scan.py

# Quick scan — one repo, no commit history
cd ~/.agents/skills/github-secrets-scan && python3 scripts/scan.py --repos TopNiz/finperso --no-commits

# Scan a specific account only
cd ~/.agents/skills/github-secrets-scan && python3 scripts/scan.py --account dotit-bot

# Exclude forks, no commit history (fastest)
cd ~/.agents/skills/github-secrets-scan && python3 scripts/scan.py --no-forks --no-commits

# Full scan + AI classification (filters test data automatically)
cd ~/.agents/skills/github-secrets-scan && python3 scripts/scan.py --ai-classify

# Scan + interactive review to mark findings as normal/resolved
cd ~/.agents/skills/github-secrets-scan && python3 scripts/scan.py --mitigate

# Second scan: AI only classifies new findings, DB handles known ones
cd ~/.agents/skills/github-secrets-scan && python3 scripts/scan.py --ai-classify

# List all mitigated findings
cd ~/.agents/skills/github-secrets-scan && python3 scripts/mitigation_db.py stats
```
