#!/usr/bin/env python3
"""Gmail OAuth2 with separate file credentials for primary accounts.

When accounts.gmail/default-account.json exists, local and SSH sessions use
private account token files and a shared client file without native-store
access. Select a primary account through get_service(account=...), --account,
or PI_EMAIL_MANAGER_ACCOUNT. No selection preserves the configured default.

Without this configuration, legacy stores remain supported: macOS interactive
Keychain, macOS SSH JSON files, Linux Secret Service/systemd credentials, and
Windows JSON files. Native-store migration is disabled for configured accounts.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
VENV_DIR = SKILL_DIR / ".venv"
VENV_PYTHON = VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
_RUNNING_IN_VENV_ENV = "PI_EMAIL_MANAGER_IN_VENV"
KEYRING_SERVICE = "pi-email-manager.gmail-oauth"
CLIENT_ACCOUNT = "client-config"
TOKEN_ACCOUNT = "user-credentials"
SYSTEMD_CREDENTIAL_NAMES = {
    CLIENT_ACCOUNT: "gmail-oauth-client",
    TOKEN_ACCOUNT: "gmail-oauth-token",
}


def _force_utf8_stdio() -> None:
    """Make stdout/stderr UTF-8 on every platform.

    Windows consoles default to a legacy code page (cp1252 here), which raises
    UnicodeEncodeError as soon as a script prints an emoji or a non-ASCII email
    subject. Reconfiguring keeps output identical across platforms.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):  # non-reconfigurable stream
            pass


def _venv_site_packages() -> Path | None:
    """site-packages of the skill venv, for entry points we cannot re-exec."""
    if os.name == "nt":
        return VENV_DIR / "Lib" / "site-packages"
    return VENV_DIR / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"


def _ensure_skill_venv() -> None:
    """Re-exec under the uv-managed skill venv declared in ``pyproject.toml``.

    ``uv sync`` installs the Gmail API and credential-store dependencies into
    ``<skill>/.venv``. Calling the scripts with any other interpreter would miss
    them, so transparently re-exec into that venv when needed.

    Never install these dependencies with ``pip install --target``: on Windows
    pip stages wheels in a ``mkdtemp()`` (mode 0o700) tree and moves them into
    place, which stamps an owner-only, inheritance-breaking DACL on every
    installed file and locks the dependencies out of non-owner accounts.
    """
    if os.environ.get(_RUNNING_IN_VENV_ENV) == "1" or not VENV_PYTHON.is_file():
        return
    # Detect the venv via sys.prefix, not by comparing executable paths: on POSIX
    # .venv/bin/python is a symlink to the base interpreter, so a resolved-path
    # comparison reports "already inside the venv" and the bootstrap does nothing.
    if Path(sys.prefix).resolve() == VENV_DIR.resolve():
        return
    # subprocess (not os.execv) so stdout/stderr stay attached: on Windows
    # execv exits the parent before the child writes, losing piped output.
    # Only re-exec when sys.argv[0] is a real script we can replay; for piped
    # stdin (`python3 - < script`) or `-c` we fall back to importing the venv's
    # packages in-process, since replaying an exhausted stdin would silently
    # run nothing.
    entry = sys.argv[0] if sys.argv else ""
    if entry and entry != "-" and Path(entry).is_file():
        os.environ[_RUNNING_IN_VENV_ENV] = "1"
        result = subprocess.run([str(VENV_PYTHON), *sys.argv], env=os.environ)
        raise SystemExit(result.returncode)

    site_packages = _venv_site_packages()
    if site_packages and site_packages.is_dir() and str(site_packages) not in sys.path:
        sys.path.insert(0, str(site_packages))


_force_utf8_stdio()
_ensure_skill_venv()

if sys.platform == "darwin":
    try:
        import keyring
        from keyring.errors import KeyringError
    except ImportError:  # File-based accounts do not require keyring.
        keyring = None

        class KeyringError(Exception):
            pass

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
LEGACY_CLIENT_FILE = SKILL_DIR / "credentials.gmail.json"
LEGACY_TOKEN_FILE = SKILL_DIR / "token.gmail.json"

# Opt into a file-based token store instead of the OS credential store. This
# is the only store on Windows (Credential Manager fails with WinError 1312 for
# processes without an interactive logon session) and is always used there; on
# macOS/Linux it is opt-in:
#   set PI_EMAIL_MANAGER_TOKEN_FILE=/path/to/token.gmail.json
TOKEN_FILE_ENV = "PI_EMAIL_MANAGER_TOKEN_FILE"
ACCOUNT_ENV = "PI_EMAIL_MANAGER_ACCOUNT"
ACCOUNTS_DIR = SKILL_DIR / "accounts.gmail"
MANAGED_CLIENT_FILE = ACCOUNTS_DIR / "credentials.gmail.json"
DEFAULT_ACCOUNT_FILE = ACCOUNTS_DIR / "default-account.json"


def _normalize_account(account: str) -> str:
    account = account.strip().lower()
    if not re.fullmatch(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", account):
        raise CredentialStoreError("Use a primary Gmail account address, not a path or alias.")
    return account


def _default_account() -> str:
    try:
        data = json.loads(DEFAULT_ACCOUNT_FILE.read_text(encoding="utf-8"))
        return _normalize_account(data["account"])
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise CredentialStoreError("The file-based default account configuration is invalid.") from error


def _account_token_file(account: str) -> Path:
    return ACCOUNTS_DIR / _normalize_account(account) / "token.gmail.json"


def list_accounts() -> list[str]:
    """List provisioned primary accounts without reading credential values."""
    if not ACCOUNTS_DIR.is_dir():
        return []
    accounts = []
    for directory in ACCOUNTS_DIR.iterdir():
        if directory.is_dir() and (directory / "token.gmail.json").is_file():
            accounts.append(_normalize_account(directory.name))
    return sorted(accounts)


class CredentialStoreError(RuntimeError):
    """Raised when native credential storage cannot be accessed safely."""


def _secret_tool(*args: str, value: str | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["secret-tool", *args],
            input=value,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CredentialStoreError("The native credential store is unavailable.") from error


def _systemd_credential_path(account: str) -> Path | None:
    directory = os.environ.get("CREDENTIALS_DIRECTORY")
    name = SYSTEMD_CREDENTIAL_NAMES.get(account)
    if not directory or not name:
        return None
    path = Path(directory) / name
    return path if path.is_file() else None


def _file_secret_path(account: str) -> Path | None:
    """File backing the store for ``account`` on Windows."""
    if account == TOKEN_ACCOUNT:
        return LEGACY_TOKEN_FILE
    if account == CLIENT_ACCOUNT:
        return LEGACY_CLIENT_FILE
    return None


def _get_secret(account: str) -> str | None:
    if DEFAULT_ACCOUNT_FILE.is_file():
        path = MANAGED_CLIENT_FILE if account == CLIENT_ACCOUNT else _token_file()
        return path.read_text(encoding="utf-8") if path and path.is_file() else None

    systemd_path = _systemd_credential_path(account)
    if systemd_path:
        return systemd_path.read_text(encoding="utf-8")

    if sys.platform == "darwin" and os.environ.get("SSH_CONNECTION"):
        path = LEGACY_CLIENT_FILE if account == CLIENT_ACCOUNT else LEGACY_TOKEN_FILE
        return path.read_text(encoding="utf-8") if path.is_file() else None

    if sys.platform == "win32":
        # Windows Credential Manager is deliberately not used: non-interactive
        # and sandboxed sessions cannot reach it (WinError 1312), so the file
        # store is the only store there.
        path = _file_secret_path(account)
        return path.read_text(encoding="utf-8") if path and path.is_file() else None

    if sys.platform == "darwin":
        if keyring is None:
            raise CredentialStoreError("Native credential storage requires the keyring package.")
        try:
            return keyring.get_password(KEYRING_SERVICE, account)
        except KeyringError as error:
            raise CredentialStoreError("The native credential store is unavailable.") from error
        except OSError as error:
            raise CredentialStoreError(_store_hint(error)) from error

    if sys.platform == "linux":
        result = _secret_tool("lookup", "service", KEYRING_SERVICE, "account", account)
        if result.returncode != 0:
            return None
        return result.stdout.removesuffix("\n")

    raise CredentialStoreError("No supported native credential store is available.")


def _store_hint(error: OSError) -> str:
    """Explain credential-store OSErrors, notably WinError 1312."""
    hint = (
        "the OS credential store rejected the request; a process without an "
        "interactive logon session cannot use CredWrite (WinError 1312)"
    )
    return f"{error} - {hint}. Set {TOKEN_FILE_ENV} to a token file instead."


def _token_file() -> Path | None:
    """Resolve a token override, selected account, default, or legacy file.

    Configured accounts use the same files locally and over SSH. The explicit
    token-file environment override takes precedence over implicit selection.
    """
    value = os.environ.get(TOKEN_FILE_ENV, "").strip()
    if value:
        return Path(value).expanduser()
    selected_account = os.environ.get(ACCOUNT_ENV)
    if selected_account:
        return _account_token_file(selected_account)
    if DEFAULT_ACCOUNT_FILE.is_file():
        return _account_token_file(_default_account())
    if sys.platform == "darwin" and os.environ.get("SSH_CONNECTION"):
        return LEGACY_TOKEN_FILE
    if sys.platform == "win32":
        return LEGACY_TOKEN_FILE
    return None


def _write_token_file(path: Path, creds: Credentials) -> None:
    """Persist credentials to a file, inheriting the directory's permissions.

    This is the primary credential store on Windows, so it deliberately does not
    create a restrictive DACL there: the directory's inherited permissions let a
    sandboxed agent or service account read it too. On POSIX the file is
    chmod 0600.
    """
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        os.chmod(path.parent, 0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        if os.name != "nt":
            os.fchmod(handle.fileno(), 0o600)
        handle.write(creds.to_json())


def _store_credentials(creds: Credentials, token_file: Path | None = None) -> None:
    """Save credentials to the selected account, never another account."""
    token_file = token_file if token_file is not None else _token_file()
    if token_file is not None:
        _write_token_file(token_file, creds)
        return

    if _systemd_credential_path(TOKEN_ACCOUNT):
        return  # read-only at runtime; nothing to persist

    store_error: CredentialStoreError | None = None
    try:
        _set_secret(TOKEN_ACCOUNT, creds.to_json())
        return
    except CredentialStoreError as error:
        # Do not lose the authorization: keep it in a file the caller can import.
        store_error = error

    try:
        _write_token_file(LEGACY_TOKEN_FILE, creds)
    except OSError as write_error:
        raise CredentialStoreError(
            f"Could not store credentials ({store_error}) and could not write "
            f"{LEGACY_TOKEN_FILE} either ({write_error})."
        ) from write_error

    print(f"warning: could not save to the OS credential store: {store_error}", file=sys.stderr)
    print(f"         credentials were written to {LEGACY_TOKEN_FILE} instead", file=sys.stderr)
    print("         from an interactive session, import them with:", file=sys.stderr)
    print("           python scripts/auth.py --migrate", file=sys.stderr)
    print("         or run this skill with the file store:", file=sys.stderr)
    print(f"           set {TOKEN_FILE_ENV}={LEGACY_TOKEN_FILE}", file=sys.stderr)


def _set_secret(account: str, value: str) -> None:
    if DEFAULT_ACCOUNT_FILE.is_file():
        if account != TOKEN_ACCOUNT:
            raise CredentialStoreError("Manage the shared OAuth client configuration as a private file.")
        creds = Credentials.from_authorized_user_info(json.loads(value), SCOPES)
        _write_token_file(_token_file(), creds)
        return
    if _systemd_credential_path(account):
        raise CredentialStoreError("Systemd-encrypted credentials are read-only at runtime.")

    if sys.platform == "win32":
        path = _file_secret_path(account)
        if path is None:
            raise CredentialStoreError(f"No file store is defined for account '{account}'.")
        path.write_text(value, encoding="utf-8")
        try:
            os.chmod(path, 0o600)  # POSIX-only; on Windows the DACL is inherited
        except OSError:
            pass
        return

    if sys.platform == "darwin":
        if keyring is None:
            raise CredentialStoreError("Native credential storage requires the keyring package.")
        try:
            keyring.set_password(KEYRING_SERVICE, account, value)
        except KeyringError as error:
            raise CredentialStoreError("The native credential store is unavailable.") from error
        except OSError as error:
            raise CredentialStoreError(_store_hint(error)) from error
        return

    if sys.platform == "linux":
        result = _secret_tool(
            "store",
            "--label=Pi Email Manager Gmail OAuth",
            "service",
            KEYRING_SERVICE,
            "account",
            account,
            value=value,
        )
        if result.returncode != 0:
            raise CredentialStoreError("The native credential store is unavailable.")
        return

    raise CredentialStoreError("No supported native credential store is available.")


def _load_json_secret(account: str) -> dict:
    value = _get_secret(account)
    if not value:
        raise CredentialStoreError("Gmail OAuth configuration is not available.")
    try:
        return json.loads(value)
    except json.JSONDecodeError as error:
        raise CredentialStoreError("Gmail OAuth configuration in the native credential store is invalid.") from error


def migrate_legacy_files() -> bool:
    """Move legacy local OAuth files into the native credential store safely."""
    if sys.platform == "win32":
        # The file store already *is* the store on Windows; nothing to migrate.
        return False
    sources = (
        (CLIENT_ACCOUNT, LEGACY_CLIENT_FILE),
        (TOKEN_ACCOUNT, LEGACY_TOKEN_FILE),
    )
    pending: list[tuple[str, Path, str]] = []
    for account, path in sources:
        if path.is_file():
            pending.append((account, path, path.read_text(encoding="utf-8")))

    if not pending:
        return False

    for account, _path, value in pending:
        json.loads(value)  # Validate before changing the credential store.
        _set_secret(account, value)

    for _account, path, _value in pending:
        path.unlink()
    return True


def get_credentials(account: str | None = None) -> Credentials:
    """Return valid credentials for one primary account.

    An explicit account selects its own file without fallback. Otherwise use
    the token-file override, account environment variable, configured default,
    or the legacy platform store. File-based accounts never require Keychain.
    """
    token_info = None
    token_file = _account_token_file(account) if account else _token_file()
    if token_file is not None:
        if not token_file.is_file():
            raise CredentialStoreError(
                "The selected account token file does not exist. "
                "Authorize it with 'python scripts/auth.py --login --account=primary@example.com'."
            )
        try:
            token_info = json.loads(token_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise CredentialStoreError(f"Cannot read the token file {token_file}: {error}") from error
    else:
        try:
            token_value = _get_secret(TOKEN_ACCOUNT)
        except CredentialStoreError as error:
            print(f"warning: OS credential store unavailable ({error})", file=sys.stderr)
            token_value = None
        token_info = json.loads(token_value) if token_value else None

    creds = Credentials.from_authorized_user_info(token_info, SCOPES) if token_info else None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _store_credentials(creds, token_file=token_file)
        else:
            client_config = _load_json_secret(CLIENT_ACCOUNT)
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            callback_port = int(os.environ.get("PI_EMAIL_OAUTH_PORT", "0"))
            open_browser = os.environ.get("PI_EMAIL_OAUTH_OPEN_BROWSER", "1") != "0"
            creds = flow.run_local_server(
                port=callback_port, open_browser=open_browser,
                authorization_prompt_message="Open the Google sign-in window to authorize access.",
            )
            _store_credentials(creds, token_file=token_file)

    return creds


def get_service(account: str | None = None):
    """Return a Gmail service and verify any selected primary account."""
    selected = account or os.environ.get(ACCOUNT_ENV)
    if not selected and DEFAULT_ACCOUNT_FILE.is_file() and not os.environ.get(TOKEN_FILE_ENV):
        selected = _default_account()
    service = build("gmail", "v1", credentials=get_credentials(account=account))
    if selected and get_account_email(service).lower() != _normalize_account(selected):
        raise CredentialStoreError("The stored credentials do not match the selected primary account.")
    return service


def get_account_email(service) -> str:
    """Return the authenticated Gmail address."""
    return service.users().getProfile(userId="me").execute().get("emailAddress", "unknown@unknown.com")


def _report_refresh_failure() -> int:
    print(
        "The refresh token was rejected (invalid_grant): it has been revoked or expired.",
        file=sys.stderr,
    )
    print("Run 'python3 scripts/auth.py' to authenticate again.", file=sys.stderr)
    return 1


def _check(account: str | None = None) -> int:
    """Verify the credentials and report the authenticated address.

    Loads the stored credentials, then resolves the mailbox with
    ``users.getProfile`` so the printed address is the account's Google
    **primary** address. A send-as alias that merely delivers to the same inbox
    is never returned. Exit 0 therefore means the credentials work against the
    Gmail API; 1 means the refresh token is missing, rejected, or the API could
    not be reached.
    """
    store = "file token store" if account or _token_file() is not None else "native credential storage"

    try:
        get_credentials(account=account)
    except RefreshError:
        return _report_refresh_failure()
    except CredentialStoreError as error:
        print(f"Authentication unavailable: {error}", file=sys.stderr)
        print("Run 'python3 scripts/auth.py --diagnose' for details.", file=sys.stderr)
        return 1
    except Exception:
        print("Authentication unavailable.", file=sys.stderr)
        print("Run 'python3 scripts/auth.py --diagnose' for details.", file=sys.stderr)
        return 1

    try:
        account_email = get_account_email(get_service(account=account))
    except RefreshError:
        return _report_refresh_failure()
    except Exception as error:
        print(
            f"Credentials present, but the Gmail API profile lookup failed: {error}",
            file=sys.stderr,
        )
        print(
            "Usually a network/DNS problem or an expired access token; retry, then "
            "run 'python3 scripts/auth.py --diagnose' if it persists.",
            file=sys.stderr,
        )
        return 1

    print(f"Authenticated as {account_email} using the {store}.")
    return 0


def _diagnose() -> int:
    """Explain where credentials would come from. Never prints secret values.

    Written for the case where an agent cannot authenticate: it distinguishes
    "this OS account has no refresh token" (needs an interactive browser
    consent that headless/sandboxed agents cannot perform) from "the OAuth
    client config is missing" (needs credentials.gmail.json on this machine).
    """
    print("Gmail auth diagnostics (no secret values are printed)")
    print("-" * 62)
    print(f"platform            : {sys.platform} ({os.name})")
    print(f"python              : {sys.executable}")
    in_venv = False
    try:
        in_venv = Path(sys.executable).resolve() == VENV_PYTHON.resolve()
    except OSError:
        pass
    print(f"skill venv          : {VENV_PYTHON.is_file()} (running inside it: {in_venv})")
    print(f"OS user             : {os.environ.get('USERNAME') or os.environ.get('USER', '?')}")
    print(f"skill dir           : {SKILL_DIR}")

    if DEFAULT_ACCOUNT_FILE.is_file():
        print("credential store    : separate account files (no native-store access)")
    elif sys.platform == "darwin":
        try:
            import keyring

            print(f"credential store    : keyring -> {keyring.get_keyring()}")
        except ImportError:
            print("credential store    : keyring NOT INSTALLED (run: uv sync)")
    elif sys.platform == "win32":
        print("credential store    : file store (token.gmail.json)")
    else:
        print("credential store    : secret-tool / Secret Service")

    token_value = None
    file_token = _token_file()
    if file_token is not None:
        source = "default" if sys.platform == "win32" and not os.environ.get(TOKEN_FILE_ENV) else "env"
        state = "present" if file_token.is_file() else "ABSENT"
        print(f"token file ({source:<7}) : {file_token} ({state})")
        if file_token.is_file():
            try:
                token_value = file_token.read_text(encoding="utf-8")
                json.loads(token_value)
                print(f"{'':<20}  valid JSON, in use")
            except (OSError, json.JSONDecodeError) as error:
                print(f"{'':<20}  unreadable: {error}")
                token_value = None
    else:
        print(f"token file (env)    : not set ({TOKEN_FILE_ENV})")

    for account, label in (
        (CLIENT_ACCOUNT, "client-config"),
        (TOKEN_ACCOUNT, "refresh-token"),
    ):
        try:
            value = _get_secret(account)
        except CredentialStoreError as error:
            print(f"{label:<20}: ERROR - {error}")
            continue
        print(f"{label:<20}: {'present (' + str(len(value)) + ' chars)' if value else 'ABSENT'}")
        if account == TOKEN_ACCOUNT and token_value is None:
            token_value = value

    client_ok = False
    client_file = MANAGED_CLIENT_FILE if DEFAULT_ACCOUNT_FILE.is_file() else LEGACY_CLIENT_FILE
    if client_file.is_file():
        try:
            with client_file.open(encoding="utf-8") as handle:
                json.load(handle)
            client_state = "present, readable, valid JSON"
            client_ok = True
        except OSError:
            client_state = "present but NOT readable by this OS user"
        except json.JSONDecodeError:
            client_state = "present but not valid JSON"
    else:
        client_state = "ABSENT"
    print(f"file client-config  : {client_file}")
    print(f"{'':<20}  {client_state}")

    print("-" * 62)
    if not token_value:
        print("RESULT: no refresh token available to this process.")
        if file_token is not None and not file_token.is_file():
            print(f"        Expected token file is missing: {file_token}")
            print("        Create it on an authenticated machine with:")
            print("          python scripts/auth.py --export <path>")
            print("        ...or run 'python3 scripts/auth.py' interactively once.")
        elif client_ok:
            print("        The OAuth client config IS available, so the next auth attempt")
            print("        starts an INTERACTIVE browser consent, which fails in headless")
            print("        or sandboxed agents. Provision this account/machine:")
            if sys.platform == "win32":
                print("          - copy an existing token.gmail.json into this skill dir")
                print("          - or run 'python3 scripts/auth.py' interactively once")
            else:
                print("          - copy an existing token.gmail.json here, then run")
                print("            python3 scripts/auth.py --migrate")
                print("          - or run 'python3 scripts/auth.py' interactively once")
        else:
            print("        The OAuth client config is ALSO missing here, so authentication")
            print("        cannot even be started. Copy credentials.gmail.json to this")
            print("        machine (it is gitignored), then run 'python3 scripts/auth.py'.")
        print("        See 'Authentication' in SKILL.md.")
        return 1

    try:
        creds = Credentials.from_authorized_user_info(json.loads(token_value), SCOPES)
    except (ValueError, KeyError) as error:
        print(f"RESULT: stored token is unreadable: {error}")
        return 1

    if creds.valid:
        print("RESULT: refresh token present, access token still valid. OK.")
        return 0

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as error:  # noqa: BLE001 - report any refresh failure
            print(f"RESULT: token present but refresh FAILED: {type(error).__name__}: {error}")
            print("        Revoked or expired? Re-run: python3 scripts/auth.py")
            return 1
        _store_credentials(creds)
        print("RESULT: refresh token present, access token renewed. OK.")
        return 0

    print("RESULT: token present but unusable (no refresh_token). Re-authenticate.")
    return 1


def _export(destination: str, account: str | None = None) -> int:
    """Write the stored OAuth credentials to a file, to provision another host.

    The file contains a refresh token, so it is a secret: transfer it over a
    trusted channel, place/import it on the target, then delete it.
    """
    target = Path(destination).expanduser()
    if target.exists():
        print(f"Refusing to overwrite existing file: {target}", file=sys.stderr)
        return 1
    try:
        if account:
            source = _account_token_file(account)
            value = source.read_text(encoding="utf-8") if source.is_file() else None
        else:
            value = _get_secret(TOKEN_ACCOUNT)
    except (CredentialStoreError, OSError) as error:
        print(f"Cannot read the credential store: {error}", file=sys.stderr)
        return 1
    if not value:
        print("No stored credentials to export. Authenticate first.", file=sys.stderr)
        return 1
    try:
        json.loads(value)
    except json.JSONDecodeError as error:
        print(f"Stored credentials are not valid JSON: {error}", file=sys.stderr)
        return 1

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        handle.write(value)
    try:
        os.chmod(target, 0o600)  # POSIX only; on Windows os.chmod cannot set ACLs
    except OSError:
        pass

    print(f"Exported credentials to: {target}")
    print("This file holds a refresh token for the Gmail modify scope:", file=sys.stderr)
    print("  - transfer it over a trusted channel only", file=sys.stderr)
    print("  - place it as token.gmail.json on the target (Windows) or import it", file=sys.stderr)
    print("    with 'python3 scripts/auth.py --migrate' (macOS/Linux)", file=sys.stderr)
    print("  - delete it afterwards (token.gmail.json is gitignored)", file=sys.stderr)
    return 0


def _login_account(account: str) -> int:
    """Authorize a new named account without replacing an existing token."""
    account = _normalize_account(account)
    destination = _account_token_file(account)
    if destination.exists():
        print("Account already exists. Use --check with --account to verify it.", file=sys.stderr)
        return 1
    client_config = _load_json_secret(CLIENT_ACCOUNT)
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(
        port=int(os.environ.get("PI_EMAIL_OAUTH_PORT", "0")),
        open_browser=os.environ.get("PI_EMAIL_OAUTH_OPEN_BROWSER", "1") != "0",
        authorization_prompt_message="Complete Google sign-in in the browser window.",
        timeout_seconds=int(os.environ.get("PI_EMAIL_OAUTH_TIMEOUT", "180")),
        login_hint=account, prompt="select_account consent",
    )
    service = build("gmail", "v1", credentials=creds)
    if get_account_email(service).lower() != account:
        print("Google authorized a different primary account. Nothing was saved.", file=sys.stderr)
        return 1
    _write_token_file(destination, creds)
    print(f"Saved authorization for {account} in the separate file token store.")
    return 0


def main(argv: list[str]) -> int:
    account = None
    for index, arg in enumerate(argv):
        if arg.startswith("--account="):
            account = _normalize_account(arg.split("=", 1)[1])
        elif arg == "--account" and index + 1 < len(argv):
            account = _normalize_account(argv[index + 1])

    if "--list-accounts" in argv:
        for address in list_accounts():
            print(address)
        return 0

    if "--login" in argv:
        if not account:
            print("Usage: auth.py --login --account=primary@example.com", file=sys.stderr)
            return 1
        return _login_account(account)

    if "--migrate" in argv:
        if DEFAULT_ACCOUNT_FILE.is_file():
            print("File-based accounts are enabled. Native-store migration is disabled.", file=sys.stderr)
            return 1
        if sys.platform == "win32":
            print("Windows stores Gmail credentials in token.gmail.json; nothing to migrate.")
            return 0
        try:
            migrated = migrate_legacy_files()
        except (CredentialStoreError, OSError, json.JSONDecodeError):
            print("Credential migration failed; legacy files were retained.", file=sys.stderr)
            return 1
        print("Legacy OAuth files migrated to native credential storage." if migrated else "No legacy OAuth files found to migrate.")
        return 0

    if "--check" in argv:
        return _check(account=account)

    if "--diagnose" in argv:
        return _diagnose()

    for index, arg in enumerate(argv):
        if arg == "--export":
            if index + 1 >= len(argv):
                print("Usage: auth.py --export <path>", file=sys.stderr)
                return 1
            return _export(argv[index + 1], account=account)
        if arg.startswith("--export="):
            return _export(arg.split("=", 1)[1], account=account)

    try:
        service = get_service(account=account)
        print(f"Authenticated as {get_account_email(service)}.")
    except CredentialStoreError as error:
        print(f"Authentication unavailable: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
