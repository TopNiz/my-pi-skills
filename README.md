# My Pi Skills

A personal collection of reusable **pi coding-agent skills**. Each skill lives in its own directory and is documented by a `SKILL.md` file that tells the agent when and how to use it.

This repository is intended to be cloned to:

```bash
~/.agents/skills
```

## Skill catalog

| Skill | Purpose | Main docs |
|---|---|---|
| `ideation` | Record, detail, and track your ideas — quick-log or deep-dive with notes. | [`ideation/SKILL.md`](ideation/SKILL.md) |
| `md2pdf` | Convert Markdown to styled A4 PDFs via pandoc + weasyprint, with a replaceable default style and a fix for the pandoc 3.9 variation-selector glyph bug. | [`md2pdf/SKILL.md`](md2pdf/SKILL.md) |
| `ai-usage` | Check account usage, costs, balances, and access across OpenAI, DeepSeek, and Ollama Cloud. | [`ai-usage/SKILL.md`](ai-usage/SKILL.md) |
| `email-manager` | Fetch IMAP email, categorize messages, detect urgency, prepare reviews, and extract invoices. | [`email-manager/SKILL.md`](email-manager/SKILL.md) |
| `describe-image` | Describe images in detail using pi with a vision-capable model. | [`describe-image/SKILL.md`](describe-image/SKILL.md) |
| `extract-text` | Extract text and OCR images/PDFs using the protected Apache Tika service. | [`extract-text/SKILL.md`](extract-text/SKILL.md) |
| `nextcloud` | Administer and troubleshoot Nextcloud with the `occ` command. | [`nextcloud/SKILL.md`](nextcloud/SKILL.md) |
| `openai-image` | Generate and edit images with OpenAI `gpt-image-*` models. | [`openai-image/SKILL.md`](openai-image/SKILL.md) |
| `physical-scanner` | Scan paper documents to PDF via AirPrint/eSCL network scanners. | [`physical-scanner/SKILL.md`](physical-scanner/SKILL.md) |
| `preview-manager` | Control macOS Preview.app documents with AppleScript. | [`preview-manager/SKILL.md`](preview-manager/SKILL.md) |
| `ssh-skills` | SSH, SCP, rsync, tunnels, tmux, and tag-based remote host operations. | [`ssh-skills/SKILL.md`](ssh-skills/SKILL.md) |
| `web-browser` | Browse, inspect, automate, and test websites with Playwright. | [`web-browser/SKILL.md`](web-browser/SKILL.md) |
| `web-search` | Perform web searches using Playwright, usually in a headed browser to avoid bot blocks. | [`web-search/SKILL.md`](web-search/SKILL.md) |

## Repository layout

```text
.
├── README.md
├── deploy.sh
├── .gitignore
├── ideation/
├── md2pdf/
├── ai-usage/
├── email-manager/
├── describe-image/
├── extract-text/
├── nextcloud/
├── openai-image/
├── physical-scanner/
├── preview-manager/
├── ssh-skills/
├── web-browser/
├── write-html/
└── web-search/
```

Each skill directory normally contains:

- `SKILL.md` — the agent-facing instructions and examples.
- helper scripts, if needed by the skill.
- `references/`, if the skill has extra documentation.
- templates/examples for local configuration, where applicable.

## Installation

Clone the repository into the agent skills directory:

```bash
mkdir -p ~/.agents
git clone git@github.com:TopNiz/my-pi-skills.git ~/.agents/skills
```

To update an existing clone:

```bash
cd ~/.agents/skills
git pull
```

## Secrets and local configuration

This repository is public, so secrets must stay local to each machine.

The `.gitignore` excludes common secret and machine-local files:

```gitignore
.env
**/config.json
**/user_preferences.json
**/__pycache__/
**/.playwright-cli/
*.pyc
*.pyo
.DS_Store
```

Before committing, it is still worth checking what Git will publish:

```bash
cd ~/.agents/skills
git status --short
git diff --cached --stat
git ls-files
```

### AI usage environment

The `ai-usage` skill provides an environment template:

```bash
cp ~/.agents/skills/ai-usage/.env.example ~/.pi/agent/.env
chmod 600 ~/.pi/agent/.env
$EDITOR ~/.pi/agent/.env
```

Supported keys in that file include:

```bash
OPENAI_ADMIN_KEY=...
DEEPSEEK_KEY=...
OLLAMA_CLOUD_KEY=...
# Optional, machine-specific:
# OLLAMA_SERVER_URL=http://your-server:11434/v1
```

`~/.pi/agent/.env` is intentionally outside this repository and should be configured separately on every host.

### Email manager configuration

The email manager uses a local JSON config file that is ignored by Git:

```bash
cd ~/.agents/skills/email-manager
chmod +x scripts/setup.sh
./scripts/setup.sh
```

Or configure it manually from the template:

```bash
cp scripts/config.template.json scripts/config.json
$EDITOR scripts/config.json
```

For Gmail, enable IMAP and use an app password rather than your normal account password.

### Other local state

Some skills rely on machine-local tools or configuration:

- `extract-text` uses a local git-ignored `.env` file for the protected Tika service credentials.
- `google-calendar` uses local git-ignored `credentials.json` and `token.json` OAuth files.
- `ssh-skills` uses the local SSH config and keys.
- `preview-manager` requires macOS Preview.app and GUI AppleScript access.
- `web-browser` and `web-search` use Playwright / `playwright-cli` and may create local browser/session data.
- `nextcloud` depends on access to the target Nextcloud host/container and its `occ` command.

Do not commit local credentials, host-specific private details, browser sessions, or generated caches.

## Deployment workflow

Deployment is handled by [`deploy.sh`](deploy.sh).

```bash
cd ~/.agents/skills
./deploy.sh
```

With no arguments, the script commits local changes, pushes them to GitHub, and stops.

To also update one or more remote machines:

```bash
./deploy.sh codimeo.com
./deploy.sh pc-vm-fedora-1.local
./deploy.sh codimeo.com pc-vm-fedora-1.local
```

### What `deploy.sh` does

1. Resolves the repository directory from the location of `deploy.sh`.
2. Changes into that directory.
3. Prints `git status --short --branch` before doing anything destructive.
4. If there are staged, unstaged, deleted, or untracked non-ignored files, it reviews the status before committing:
   - shows the files that `git add -A` would include;
   - checks changed paths for obvious sensitive filenames such as `.env`, `*.pem`, `*.key`, `auth.json`, `config.json`, `user_preferences.json`, secrets, credentials, or tokens;
   - asks `pi` for a no-session, no-tools agent review of the Git status with:

     ```bash
     pi --no-session --no-tools --no-extensions --no-skills --no-prompt-templates --no-context-files --mode text -p "...status review prompt..."
     ```

   - if either the filename check or the pi review flags caution, the script asks for confirmation before continuing.
5. If confirmed, or if no caution is flagged, it runs `git add -A`.
6. Commits everything with a timestamped message like `Update skills — YYYY-MM-DD HH:MM`.
7. Pushes the current branch to GitHub with `git push`.
8. If hostnames were provided as arguments, SSHes into each host and runs:

   ```bash
   cd ~/.agents/skills && git pull
   ```

9. Prints a reminder that every machine needs its own local secrets file.

### Important deployment notes

- `deploy.sh` commits **all** local repository changes, including deletions and untracked non-ignored files.
- The script now displays Git status and asks pi for a no-session review before auto-committing changes.
- If pi flags caution, or if suspicious sensitive-looking paths are detected, the script requires interactive confirmation.
- For non-interactive automation, set `DEPLOY_ASSUME_YES=1` only when you intentionally accept the risk.
- The script does **not** copy `.env` files or other ignored secrets to remote hosts.
- Each remote host must already have this repository cloned at `~/.agents/skills`.
- Each remote host must have Git installed and SSH access configured.
- Each remote host must manage its own `~/.pi/agent/.env` and other machine-local configs.
- The SSH command uses `RemoteCommand=none` and `RequestTTY=no`, so it is intended for non-interactive pulls.

First-time setup on a remote host typically looks like:

```bash
mkdir -p ~/.agents
git clone git@github.com:TopNiz/my-pi-skills.git ~/.agents/skills
cp ~/.agents/skills/ai-usage/.env.example ~/.pi/agent/.env
chmod 600 ~/.pi/agent/.env
$EDITOR ~/.pi/agent/.env
```

After that, updates can be pushed from the main machine with:

```bash
cd ~/.agents/skills
./deploy.sh remote-hostname
```

## Working on a skill

1. Edit the relevant `SKILL.md` or helper scripts.
2. Test locally.
3. Review changes:

   ```bash
   git status --short
   git diff
   ```

4. Deploy when ready:

   ```bash
   ./deploy.sh
   # or:
   ./deploy.sh host1 host2
   ```

## Security checklist for this public repository

Before pushing, verify that you are not publishing secrets or private machine details:

```bash
git status --short
git diff --cached
git ls-files | grep -E '(^|/)(\.env|config\.json|credentials\.json|token\.json|user_preferences\.json)$' || true
```

If a sensitive file was accidentally tracked, remove it from Git while keeping the local copy:

```bash
git rm --cached path/to/sensitive-file
```

Then commit the removal and rotate any exposed credentials if necessary.
