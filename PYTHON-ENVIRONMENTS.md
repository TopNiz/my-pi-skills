# Python environments in this repository

How Python dependencies are declared, installed, and loaded by the skills — plus the
Windows ACL trap that motivated the change.

**Audit and migration performed on `<machine>`** (Windows 11 `10.0.26200.9457`,
uv `0.11.3`, uv-managed CPython `3.13.9`, keyring backend `WinVaultKeyring`).

---

## 1. The standard: uv + `pyproject.toml` + `.venv`

Every skill that needs PyPI packages:

1. declares them in `<skill>/pyproject.toml` and commits the resolved `<skill>/uv.lock`;
2. gets its environment with `uv sync` → `<skill>/.venv` (gitignored, per machine);
3. re-execs into that venv from its entry-point script, so the skill works no matter
   which interpreter the agent happens to call.

```bash
cd ~/.agents/skills
./uv-sync-all.sh              # sync every skill that has a pyproject.toml
./uv-sync-all.sh --upgrade    # also refresh uv.lock
```

`uv-sync-all.sh` is also run automatically by `deploy.sh` on each remote host after
`git pull`, because `.venv/` is never committed — every machine builds its own.

### Canonical bootstrap snippet

Paste this **before** the third-party imports of a skill's entry point (the module that
other scripts import, so one edit covers all of them):

```python
_VENV_PYTHON = SKILL_DIR / ".venv" / (
    "Scripts" if os.name == "nt" else "bin"
) / ("python.exe" if os.name == "nt" else "python")
_RUNNING_IN_VENV_ENV = "PI_<SKILL>_IN_VENV"          # must be unique per skill


def _force_utf8_stdio() -> None:
    """Windows consoles default to a legacy code page (cp1252) and raise
    UnicodeEncodeError on emoji / non-ASCII output."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass


def _venv_site_packages() -> Path:
    """site-packages of the skill venv, for entry points we cannot re-exec."""
    if os.name == "nt":
        return SKILL_DIR / ".venv" / "Lib" / "site-packages"
    return (SKILL_DIR / ".venv" / "lib"
            / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages")


def _ensure_skill_venv() -> None:
    """Re-exec under the uv-managed skill venv declared in pyproject.toml."""
    if os.environ.get(_RUNNING_IN_VENV_ENV) == "1" or not _VENV_PYTHON.is_file():
        return
    if os.path.realpath(sys.executable) == os.path.realpath(str(_VENV_PYTHON)):
        return
    # subprocess (not os.execv) so stdout/stderr stay attached: on Windows
    # execv exits the parent before the child writes, losing piped output.
    # Only re-exec when sys.argv[0] is a real script we can replay; for piped
    # stdin (`python3 - < script`) or `-c` use the venv's packages in-process,
    # since replaying an exhausted stdin would silently run nothing.
    entry = sys.argv[0] if sys.argv else ""
    if entry and entry != "-" and Path(entry).is_file():
        os.environ[_RUNNING_IN_VENV_ENV] = "1"
        raise SystemExit(
            subprocess.run([str(_VENV_PYTHON), *sys.argv], env=os.environ).returncode
        )

    site_packages = _venv_site_packages()
    if site_packages.is_dir() and str(site_packages) not in sys.path:
        sys.path.insert(0, str(site_packages))


_force_utf8_stdio()
_ensure_skill_venv()
```

Four non-obvious details, all learned the hard way:

- **`subprocess`, not `os.execv`.** On Windows `execv` terminates the parent before the
  child writes, so output going to a pipe (agent-captured stdout, `| head`, CI logs) is
  silently dropped. The child ran fine; the result was thrown away.
- **The guard env var must be unique per skill.** A shared name leaks: if skill A
  re-execs with the guard set and then spawns skill B's script as a child process, B
  would skip its own bootstrap and run under A's venv.
- **Only replay entry points that exist.** A script fed on stdin (`python3 - < script`) cannot
  be replayed: the child inherits an exhausted stdin and runs *nothing*, so the caller sees a
  silent success with no output. Re-exec only when `sys.argv[0]` is a real file; otherwise
  inject the venv's `site-packages` into `sys.path` for the current interpreter.
- **Force UTF-8 stdio.** `google-calendar` crashed with `UnicodeEncodeError` on its own
  status emoji under the cp1252 console, and `email-manager`'s `ensure_ascii=False` JSON
  broke the same way on non-ASCII subjects. Reconfiguring the streams fixes the whole
  class and makes output identical on Linux, macOS and Windows.

If `.venv` is absent the bootstrap does nothing and the script behaves as before, so a
fresh clone is never *worse* than before running `uv sync` — it just reports the missing
import.

---

## 2. Inventory: which skills use Python

23 `.py` files across 7 skills. Only three need third-party packages.

| Skill | Python | Third-party deps | Environment |
|---|---|---|---|
| `email-manager` | 4 scripts | `google-auth`, `google-auth-oauthlib`, `google-api-python-client`, `keyring`¹ | **`pyproject.toml` + `.venv`** (migrated) |
| `google-calendar` | 3 scripts | `google-auth`, `google-auth-oauthlib`, `google-api-python-client` | **`pyproject.toml` + `.venv`** (migrated) |
| `coinbase` | 1 script | `python-dotenv` | **`pyproject.toml` + `.venv`** (migrated) |
| `ai-usage` | 6 scripts | none (stdlib `urllib`) | system interpreter |
| `github-secrets-scan` | 4 scripts | none (stdlib) | system interpreter |
| `email-authoring` | 3 scripts | none (stdlib `imaplib`/`smtplib`) | system interpreter |
| `video-transcribe-diarize` | 2 scripts | none (stdlib) | system interpreter |

¹ `keyring` carries a `sys_platform == 'darwin' or sys_platform == 'win32'` marker; Linux
uses the system `secret-tool` instead.

Skills that invoke Python but ship no Python code: `freebox`, `md2pdf`, `physical-scanner`,
`scaleway`, `openwebui-remote` (the last one installs its CLI with `uv tool install`, which
was already correct). `md2pdf` depends on the **system binaries** `pandoc` and `weasyprint`,
which are outside uv's scope — see §7.

---

## 3. Root cause: the `pip install --target` ACL trap

`email-manager` originally installed its dependencies with:

```bash
python3 -m pip install --target .deps -r requirements-keyring.txt    # ← broken
```

On Windows this stamps an owner-only, **inheritance-breaking** DACL on every installed
file. Measured on this machine:

| Tree | Entries | Missing `CodexSandboxUsers` ACE | Protected DACL (`D:P`) |
|---|---|---|---|
| `.deps` (pip `--target`) | 3127 | **3127** | all |
| `.venv` (uv `sync`) | 2184 | **0** | **0** |

Resulting DACL on `.deps/keyring`:

```
D:P(A;OICI;FA;;;OW)(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)
   └ protected   └ OWNER RIGHTS  └ SYSTEM     └ Administrators
```

`OW` is `OWNER RIGHTS` (`S-1-3-4`): it grants FullControl **only when the caller is the
object's owner**. Everyone else — sandboxed agent accounts, other local users, services —
is denied. Because the owner (`%USERNAME%`) is unaffected, the damage is invisible from a
normal shell: the skill works, and only sandboxed/external tooling fails.

### Why `--target` specifically

`pip install <pkg>` (into a venv) extracts wheels straight into `site-packages` and
inherits ACLs correctly. `--target` is different — it stages first:

1. `commands/install.py:520` → `_handle_target_dir(target_dir, target_temp_dir, upgrade)`
2. `target_temp_dir` comes from `temp_dir.py:175` → `tempfile.mkdtemp(prefix="pip-target-")`
   → **mode `0o700`**
3. wheels are installed *inside* that `0o700` tree, inheriting its DACL
4. `install.py:579` → `shutil.move(lib_dir/item, target_item_dir)` — a same-volume rename,
   so **the DACL travels with the object** into `.deps`

CPython maps a non-default `mode` to a real Windows security descriptor. Verified directly:

| call | resulting DACL |
|---|---|
| `os.mkdir(p)` | `D:AI(...)` — inherits, sandbox ACE present ✅ |
| `os.mkdir(p, 0o700)` | `D:P(...OW)(...SY)(...BA)` — sandbox ACE gone ❌ |
| `os.makedirs(p, mode=0o700)` | same broken DACL ❌ |
| `tempfile.mkdtemp()` | same broken DACL ❌ |

And the same isolation test, end to end:

| install method | sandbox ACE preserved? |
|---|---|
| `pip install` → venv `site-packages` | ✅ |
| `pip install --target DIR` | ❌ |
| `uv pip install --target DIR` | ✅ |
| `uv sync` | ✅ |

`.deps` root itself kept a correct inherited DACL while **all 3127 children** were
broken — the exact fingerprint of "children moved in from a `0o700` temp dir".

### Rules

- **Never** `pip install --target` in a skills tree.
- **Never** reintroduce `requirements*.txt` for these skills; `pyproject.toml` + `uv.lock`
  is the source of truth.
- Repairing an already-damaged tree (works, verified on 1638 files, 0 failures):
  ```powershell
  icacls "<dir>" /reset /T /C /Q
  ```
  This drops the `D:P` protection flag and re-propagates the inherited ACEs. Reinstalling
  in place does **not** repair it — a new install inherits from the still-broken parent,
  so delete the tree first (`rm -rf .deps`).

---

## 4. What changed

| Path | Change |
|---|---|
| `email-manager/pyproject.toml` | **new** — declares the Gmail API + `keyring` deps, `[tool.uv] package = false` |
| `email-manager/uv.lock` | **new** — pinned resolution (35 packages), committed |
| `email-manager/scripts/auth.py` | venv bootstrap replaces the `.deps` `sys.path.insert` hack; UTF-8 stdio guard; error message points at `uv sync`; new `--diagnose` and `--export` commands; keyring `OSError` wrapped (a raw `WinError 1312` used to escape); a failed vault write no longer discards the token; optional file token store via `PI_EMAIL_MANAGER_TOKEN_FILE` |
| `email-manager/requirements-keyring.txt` | **deleted** — superseded by `pyproject.toml` |
| `email-manager/.deps/` | **deleted** — 137 MB, ACL-damaged, replaced by `.venv` |
| `email-manager/SKILL.md` | setup step now `uv sync`; boxed warning on the `--target` trap; file tree + runtime section updated |
| `email-manager/scripts/setup.sh` | **rewritten** — uv-based; validates `uv`, runs `uv sync`, creates `config.json` from the template, runs the OAuth2 `auth.py` flow. The old version was IMAP/app-password era and wrote a config key (`imap`) the current code never reads |
| `email-manager/scripts/config.template.json` | **rewritten** to the schema the code actually reads (`filters`, `invoices`, `protected_senders`, `routing`) — no passwords |
| `email-manager/scripts/extract_invoices.py` | UTF-8 reads/writes — `json.load`/`json.dump` used the locale encoding and crashed on the first non-ASCII email under cp1252 |
| `email-manager/scripts/fetch_emails.py` | config read forced to UTF-8 |
| `google-calendar/scripts/auth.py` | token written as UTF-8; comment documenting that `os.chmod` cannot restrict a DACL on Windows |
| `google-calendar/pyproject.toml` + `uv.lock` | **new** — Google API deps |
| `google-calendar/scripts/auth.py` | venv bootstrap added (covers `events.py` and `manage.py`, which `import auth`); fixes the `UnicodeEncodeError` crash on its own status emoji |
| `google-calendar/SKILL.md` | setup mentions `uv sync` |
| `coinbase/pyproject.toml` + `uv.lock` | **new** — `python-dotenv` |
| `coinbase/scripts/coinbase_readonly.py` | venv bootstrap added |
| `uv-sync-all.sh` | **new** — syncs every skill environment; safe no-op without uv |
| `deploy.sh` | remote hosts now run `git pull && ./uv-sync-all.sh` |
| `.gitattributes` | **new** — `*.sh`/`*.py` forced to LF so shebangs survive a Windows clone; `uv.lock` marked `-text` |
| `.gitignore` | added `**/.venv/` and `**/tmp/` |
| `README.md` | new "Python environments" section; corrected the stale Gmail/IMAP setup text |

`google-calendar` and `coinbase` were **unrunnable before this change**: with the
uv-managed `python3`, `import google` and `import dotenv` both failed with
`ModuleNotFoundError`. Proof of the fix:

```
$ python3 google-calendar/scripts/auth.py --check
❌ Not authenticated                 # imports resolved; no token yet (expected)

$ python3 coinbase/scripts/coinbase_readonly.py account
Error: local Coinbase credential configuration is missing   # expected on this host
```

Both had been failing earlier as `ModuleNotFoundError: No module named 'google'` /
`'dotenv'`. (`coinbase` also targets macOS paths — `REPOSITORY` is a `/Users/<mac-user>/...`
path — so it is expected to stop at "the local XRP Strategy integration is unavailable"
on Windows.)

---

## 5. Windows ACL audit of the skills tree

A full scan (excluding `.git/` and `.venv/`) found **69 entries with a protected
(`D:P`) DACL** plus **1 entry with stale inherited ACEs** — three distinct causes:

**A. Owner-only DACLs from `pip install --target`** — only `email-manager/.deps`
(3127 entries, now deleted). The severe case: no ACE at all for anything but the owner.

**B. Sandbox-written hardened DACLs** — 69 entries, still *readable* by everyone
concerned but marked `D:P` so they no longer inherit:

| Path | Entries with `D:P` |
|---|---|
| `freebox/` | 51 |
| `email-authoring/` | 11 |
| `md2pdf/` | 4 |
| `README.md` | 1 |
| `.gitignore` | 1 |
| `email-manager/SKILL.md` | 1 |

Their SDDL contains a `NULL SID` deny ACE plus write-property denies for `Users`,
`SYSTEM`, `Administrators` and `CodexSandboxUsers`, e.g.:

```
D:P(D;;SWWPDTRC;;;S-1-0-0)(A;;FA;;;<user>)(A;;0x1200a9;;;Users)
    (A;;0x1201ff;;;SY)(A;;0x1201ff;;;BA)(A;;0x1200a9;;;CodexSandboxUsers)
    (A;;0x1200a9;;;WD)(D;;WP;;;Users)(D;;WP;;;SY)(D;;WP;;;BA)(D;;WP;;;CodexSandboxUsers) ...
```

This is the fingerprint of content written by a process running under the Codex sandbox
(which owns `CodexSandboxOffline` / `CodexSandboxOnline`). Unlike case A, the sandbox ACE
*is* present, so access works today; the practical cost is that these paths no longer
follow their parent's permissions, so future permission changes on the tree skip them.

Detect, then repair if wanted:

```powershell
# detect
Get-ChildItem %USERPROFILE%\.agents\skills -Recurse -Force |
  Where-Object { $_.FullName -notmatch '\\\.git\\' -and $_.FullName -notmatch '\\\.venv\\' } |
  ForEach-Object { $a = Get-Acl $_.FullName; if ($a.Sddl -like '*D:P*') { $_.FullName } }

# repair (restores inheritance; keeps existing grants)
icacls %USERPROFILE%\.agents\skills /reset /T /C /Q
```

> Not applied — flagged for a decision, since it rewrites permissions on ~70 paths
> authored by the sandbox.

**C. Stale inherited ACEs** — 1 file: `email-manager/credentials.gmail.json` (fixed).

```
email-manager/credentials.gmail.json   D:AI(FA;SY)(FA;BA)(FA;%USERNAME%)
                                          ^ inheritance enabled, sandbox grant absent
email-manager/                         D:AI(RX;CodexSandboxUsers)(FA;SY)(FA;BA)(FA;%USERNAME%)
```

The ACEs are marked inherited but the set is **stale**: inheritable ACEs are propagated only
when the parent's ACL is written, so a file that already existed when `CodexSandboxUsers` was
granted on `.agents` keeps the older set and stays permanently denied to sandbox accounts —
while working perfectly for its owner. Same failure shape as case A from the other direction:
`OW` hides one, staleness hides the other. An audit that only looks for `D:P` and `Deny`
entries misses it.

```powershell
# detect staleness: inheritance enabled but the sandbox grant never arrived
Get-ChildItem %USERPROFILE%\.agents\skills -Recurse -Force |
  Where-Object { $_.FullName -notmatch '\\\.git\\|\\\.venv\\' } |
  ForEach-Object {
    $a = Get-Acl $_.FullName
    if ($a.Sddl -like '*D:AI*' -and
        -not ($a.Access | Where-Object { $_.IdentityReference -like '*CodexSandbox*' })) { $_.FullName }
  }
```

Repaired on 2026-09-18 with `icacls "<file>" /reset`. The file holds only the OAuth
**desktop client** config (`client_id`, `client_secret`, `project_id`, `redirect_uris`), which
Google treats as non-confidential for installed apps; the **refresh token is not in it** — it
lives in Windows Credential Manager. To undo the wider read:
`icacls "<file>" /inheritance:r /grant:r "%USERNAME%":F`.

> **General remedy.** After granting an ACE on `.agents`, re-propagate it:
> `icacls %USERPROFILE%\.agents /reset /T /C /Q`. Otherwise every pre-existing file keeps
> the old set — which is how case C happened.

> **If the goal is running the skill *inside* the sandbox**, ACLs are only half the story:
> the refresh token sits in `%USERNAME%`'s DPAPI-bound Credential Manager, which
> `CodexSandboxOffline`/`CodexSandboxOnline` cannot read (different Windows profiles). A
> sandboxed run therefore finds no token and starts an interactive OAuth flow, storing its
> own token in the sandbox account's vault. Deliberately putting the token in a file under
> `.agents` would make it group-readable — not recommended for a `gmail.modify` refresh token.
> Running the skill as `%USERNAME%` (the current setup) is the sane default.

---

## 6. Verification playbook

```bash
cd ~/.agents/skills

# 1. every skill environment builds from its lockfile
./uv-sync-all.sh

# 2. venv must inherit cleanly — expect 0 protected DACLs, all entries with the sandbox ACE
#    (PowerShell)
#    Get-ChildItem .\email-manager\.venv -Recurse -Force | ForEach-Object {
#      $a = Get-Acl $_.FullName
#      if ($a.Sddl -like '*D:P*') { $_.FullName } }

# 3. scripts must resolve their imports from any interpreter
#    (no PYTHONIOENCODING needed: the scripts force UTF-8 themselves)
python3 email-manager/scripts/auth.py --check
python3 google-calendar/scripts/auth.py --check
python3 coinbase/scripts/coinbase_readonly.py account

# 4. no pip/--target/requirements leftovers in tracked files
grep -rn "pip install --target\|requirements-keyring" --include='*.py' --include='*.md' . | grep -v '\.venv/'
```

Expected: step 3 reports *authentication/config* problems (no token, no `.env`), never
`ModuleNotFoundError`.

---

## 7. Open items and recommendations

1. **`google-calendar` stores its OAuth token in plaintext.** `token.json` inherits the
   skills-tree ACL, so `CodexSandboxUsers` (and any local `Users`/`Authenticated Users`)
   can read it. `auth.py` calls `os.chmod(TOKEN_FILE, 0o600)` for protection, but on
   Windows **`os.chmod` only toggles the read-only attribute — the DACL is unchanged**
   (verified). Recommended: migrate to `keyring`, as `email-manager` already does, or at
   minimum `icacls token.json /inheritance:r /grant:r "%USERNAME%":F`.
2. **Case B ACL repair** in §5 — apply `icacls ... /reset /T` to the 69 paths (or leave as
   is; nothing is currently inaccessible).
3. **System binaries remain unmanaged.** `md2pdf` needs `pandoc` + `weasyprint`,
   `web-browser`/`web-search` need Playwright/`npx`, `nextcloud` needs `occ`,
   `scaleway` needs the `scw` CLI. uv deliberately does not cover these; each skill
   documents its own requirements.
4. **`coinbase` has a hardcoded macOS path** (`/Users/<mac-user>/MyDocuments/002-git/xrp-strategy`)
   baked into the script rather than read from config. Worth parameterising via `.env`.
5. **`email-manager/scripts/fetch_imap_emails.py`** is the legacy IMAP fetcher, kept for
   reference. It needs no third-party packages, so it is harmless, but it is dead code
   next to the Gmail API path and could be removed.
6. **Windows Credential Manager is unusable from non-interactive processes.** An agent whose
   process has no interactive logon session gets `WinError 1312
   (ERROR_NO_SUCH_LOGON_SESSION)` from `CredWrite`: Google consent can succeed and the token
   still cannot be stored. Two mitigations now live in `email-manager/scripts/auth.py`:
   - a failed vault write keeps the token in `token.gmail.json` (gitignored) instead of
     discarding it, and prints the import recipe;
   - `PI_EMAIL_MANAGER_TOKEN_FILE=<path>` selects a file-based token store that takes
     precedence over the vault, so such an agent can read *and* write credentials.

   That file inherits the directory ACLs, which is precisely what makes it readable by a
   sandboxed agent — an intentional trade-off for a `gmail.modify` refresh token. The same
   failure class would hit any other skill storing secrets via `keyring` (none do today).
7. **Repo-wide `open()` encoding sweep (not done — 24 call sites in 4 unmodified skills).**
   Bare `open()` uses the locale encoding, so on Windows every one of these breaks on
   non-ASCII content. The writes are the dangerous ones: `video-transcribe-diarize` writes
   transcripts/C-SRT/CSV, so accented French text would fail or mangle. The four sites in
   the skills migrated here are already fixed; the rest are listed below and are a
   mechanical `encoding="utf-8"` addition:

   | File | Lines |
   |---|---|
   | `ai-usage/providers/codex.py` | 70 |
   | `ai-usage/providers/deepseek.py` | 33, 43 |
   | `ai-usage/providers/github_copilot.py` | 69, 78 |
   | `ai-usage/providers/ollama.py` | 36, 46 |
   | `ai-usage/providers/openai.py` | 32, 41 |
   | `ai-usage/providers/scaleway.py` | 64 |
   | `email-authoring/scripts/fetch_sent.py` | 132 |
   | `email-authoring/scripts/rebuild_contacts.py` | 66, 80 |
   | `email-authoring/scripts/send_email.py` | 103 |
   | `github-secrets-scan/scripts/ai_classify.py` | 348, 449 (write) |
   | `github-secrets-scan/scripts/scan.py` | 225, 396, 953 (write) |
   | `github-secrets-scan/scripts/send_email_report.py` | 87 |
   | `video-transcribe-diarize/scripts/merge_outputs.py` | 132, 138, 142, 157 (all writes) |

   Related: `google.auth`'s own `_default.py:182` reads `credentials.json` with
   `io.open(filename, "r")` — no encoding — so a non-ASCII project name in that file fails
   too. Third-party, not ours to patch.
