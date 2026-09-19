#!/usr/bin/env python3
"""Gmail API OAuth2 credentials stored only in native OS credential stores.

Run ``python3 scripts/auth.py --migrate`` once to import existing local OAuth
files into the native store. The migration deletes those files only after both
credential-store writes succeed.
"""

from __future__ import annotations

import json
import os
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
    try:
        if Path(sys.executable).resolve() == VENV_PYTHON.resolve():
            return
    except OSError:
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

if sys.platform in {"darwin", "win32"}:
    try:
        import keyring
        from keyring.errors import KeyringError
    except ImportError as error:  # pragma: no cover - environment setup error
        raise SystemExit(
            "Native credential-store support is unavailable. Run 'uv sync' in "
            f"{SKILL_DIR} to create the skill venv from pyproject.toml."
        ) from error

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
LEGACY_CLIENT_FILE = SKILL_DIR / "credentials.gmail.json"
LEGACY_TOKEN_FILE = SKILL_DIR / "token.gmail.json"

# Point the skill at a file-based token store instead of the OS credential
# store. Required for environments whose process has no interactive logon
# session (Credential Manager then fails with WinError 1312 on write):
#   set PI_EMAIL_MANAGER_TOKEN_FILE=C:\path\to\token.gmail.json
TOKEN_FILE_ENV = "PI_EMAIL_MANAGER_TOKEN_FILE"


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


def _get_secret(account: str) -> str | None:
    systemd_path = _systemd_credential_path(account)
    if systemd_path:
        return systemd_path.read_text(encoding="utf-8")

    if sys.platform in {"darwin", "win32"}:
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
    """File-based token store, if the environment opted into one."""
    value = os.environ.get(TOKEN_FILE_ENV, "").strip()
    return Path(value).expanduser() if value else None


def _write_token_file(path: Path, creds: Credentials) -> None:
    """Persist credentials to a file, inheriting the directory's permissions.

    Deliberately does not create a restrictive DACL on Windows: the whole point
    of this store is that another account (a sandboxed agent) can read it. On
    POSIX the file is chmod 0600.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(creds.to_json(), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _store_credentials(creds: Credentials) -> None:
    """Save credentials, never discarding a freshly authorized token."""
    token_file = _token_file()
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
    if _systemd_credential_path(account):
        raise CredentialStoreError("Systemd-encrypted credentials are read-only at runtime.")

    if sys.platform in {"darwin", "win32"}:
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
    # A desktop OAuth client configuration is not confidential. On Windows, keep
    # it in the ignored local skill file while the refresh token stays in
    # Windows Credential Manager.
    if not value and account == CLIENT_ACCOUNT and sys.platform == "win32" and LEGACY_CLIENT_FILE.is_file():
        value = LEGACY_CLIENT_FILE.read_text(encoding="utf-8")
    if not value:
        raise CredentialStoreError("Gmail OAuth configuration is not available.")
    try:
        return json.loads(value)
    except json.JSONDecodeError as error:
        raise CredentialStoreError("Gmail OAuth configuration in the native credential store is invalid.") from error


def migrate_legacy_files() -> bool:
    """Move legacy local OAuth files into the native credential store safely."""
    sources = ((TOKEN_ACCOUNT, LEGACY_TOKEN_FILE),) if sys.platform == "win32" else (
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


def get_credentials() -> Credentials:
    """Return valid Gmail OAuth credentials.

    Token source order: the file store named by ``PI_EMAIL_MANAGER_TOKEN_FILE``
    (if set), then the OS credential store. The file store exists because
    non-interactive sessions (services, sandboxed agents) cannot use Windows
    Credential Manager at all.
    """
    token_info = None
    token_file = _token_file()
    if token_file is not None:
        if not token_file.is_file():
            raise CredentialStoreError(
                f"{TOKEN_FILE_ENV} points at {token_file}, which does not exist. "
                "Create it with 'python scripts/auth.py --export <path>' from a "
                "machine that is already authenticated."
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
            _store_credentials(creds)
        else:
            client_config = _load_json_secret(CLIENT_ACCOUNT)
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            callback_port = int(os.environ.get("PI_EMAIL_OAUTH_PORT", "0"))
            open_browser = os.environ.get("PI_EMAIL_OAUTH_OPEN_BROWSER", "1") != "0"
            creds = flow.run_local_server(port=callback_port, open_browser=open_browser)
            _store_credentials(creds)

    return creds


def get_service():
    """Return an authenticated Gmail API service."""
    return build("gmail", "v1", credentials=get_credentials())


def get_account_email(service) -> str:
    """Return the authenticated Gmail address."""
    return service.users().getProfile(userId="me").execute().get("emailAddress", "unknown@unknown.com")


def _check() -> int:
    try:
        get_credentials()
    except CredentialStoreError as error:
        print(f"Authentication unavailable: {error}", file=sys.stderr)
        print("Run 'python3 scripts/auth.py --diagnose' for details.", file=sys.stderr)
        return 1
    except Exception:
        print("Authentication unavailable.", file=sys.stderr)
        print("Run 'python3 scripts/auth.py --diagnose' for details.", file=sys.stderr)
        return 1
    if _token_file() is not None:
        print("Authenticated using the file token store.")
    else:
        print("Authenticated with native credential storage.")
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

    if sys.platform in {"darwin", "win32"}:
        try:
            import keyring

            print(f"credential store    : keyring -> {keyring.get_keyring()}")
        except ImportError:
            print("credential store    : keyring NOT INSTALLED (run: uv sync)")
    else:
        print("credential store    : secret-tool / Secret Service")

    token_value = None
    file_token = _token_file()
    if file_token is not None:
        state = "present" if file_token.is_file() else "ABSENT"
        print(f"token file (env)    : {file_token} ({state})")
        if file_token.is_file():
            try:
                token_value = file_token.read_text(encoding="utf-8")
                json.loads(token_value)
                print(f"{'':<20}  valid JSON, takes precedence over the vault")
            except (OSError, json.JSONDecodeError) as error:
                print(f"{'':<20}  unreadable: {error}")
                token_value = None
    else:
        print(f"token file (env)    : not set ({TOKEN_FILE_ENV})")

    for account, label in (
        (CLIENT_ACCOUNT, "vault client-config"),
        (TOKEN_ACCOUNT, "vault refresh-token"),
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
    if LEGACY_CLIENT_FILE.is_file():
        try:
            with LEGACY_CLIENT_FILE.open(encoding="utf-8") as handle:
                json.load(handle)
            client_state = "present, readable, valid JSON"
            client_ok = True
        except OSError:
            client_state = "present but NOT readable by this OS user"
        except json.JSONDecodeError:
            client_state = "present but not valid JSON"
    else:
        client_state = "ABSENT"
    print(f"file client-config  : {LEGACY_CLIENT_FILE}")
    print(f"{'':<20}  {client_state}")

    print("-" * 62)
    if not token_value:
        print("RESULT: no refresh token available to this process.")
        if file_token is not None and not file_token.is_file():
            print(f"        {TOKEN_FILE_ENV} is set but {file_token} does not exist.")
            print("        Create it on an authenticated machine with:")
            print("          python scripts/auth.py --export <path>")
        elif client_ok:
            print("        The OAuth client config IS available, so the next auth attempt")
            print("        starts an INTERACTIVE browser consent, which fails in headless")
            print("        or sandboxed agents. Provision this account/machine:")
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
        if not _systemd_credential_path(TOKEN_ACCOUNT):
            _set_secret(TOKEN_ACCOUNT, creds.to_json())
        print("RESULT: refresh token present, access token renewed. OK.")
        return 0

    print("RESULT: token present but unusable (no refresh_token). Re-authenticate.")
    return 1


def _export(destination: str) -> int:
    """Write the stored OAuth credentials to a file, to provision another host.

    The file contains a refresh token, so it is a secret: transfer it over a
    trusted channel, import it with ``--migrate`` on the target, then delete it.
    """
    target = Path(destination).expanduser()
    if target.exists():
        print(f"Refusing to overwrite existing file: {target}", file=sys.stderr)
        return 1
    try:
        value = _get_secret(TOKEN_ACCOUNT)
    except CredentialStoreError as error:
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
    print("  - import on the target host: python3 scripts/auth.py --migrate", file=sys.stderr)
    print("  - delete it afterwards (token.gmail.json is gitignored)", file=sys.stderr)
    return 0


def main(argv: list[str]) -> int:
    if "--migrate" in argv:
        try:
            migrated = migrate_legacy_files()
        except (CredentialStoreError, OSError, json.JSONDecodeError):
            print("Credential migration failed; legacy files were retained.", file=sys.stderr)
            return 1
        print("Legacy OAuth files migrated to native credential storage." if migrated else "No legacy OAuth files found to migrate.")
        return 0

    if "--check" in argv:
        return _check()

    if "--diagnose" in argv:
        return _diagnose()

    for index, arg in enumerate(argv):
        if arg == "--export":
            if index + 1 >= len(argv):
                print("Usage: auth.py --export <path>", file=sys.stderr)
                return 1
            return _export(argv[index + 1])
        if arg.startswith("--export="):
            return _export(arg.split("=", 1)[1])

    try:
        service = get_service()
        print(f"Authenticated as {get_account_email(service)} using native credential storage.")
    except CredentialStoreError as error:
        print(f"Authentication unavailable: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
