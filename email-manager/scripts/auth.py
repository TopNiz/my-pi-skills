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
DEPENDENCY_DIR = SKILL_DIR / ".deps"
KEYRING_SERVICE = "pi-email-manager.gmail-oauth"
CLIENT_ACCOUNT = "client-config"
TOKEN_ACCOUNT = "user-credentials"

if DEPENDENCY_DIR.is_dir():
    sys.path.insert(0, str(DEPENDENCY_DIR))

if sys.platform == "darwin":
    try:
        import keyring
        from keyring.errors import KeyringError
    except ImportError as error:  # pragma: no cover - environment setup error
        raise SystemExit(
            "Keychain support is unavailable. Install requirements-keyring.txt before using Gmail OAuth."
        ) from error

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
LEGACY_CLIENT_FILE = SKILL_DIR / "credentials.gmail.json"
LEGACY_TOKEN_FILE = SKILL_DIR / "token.gmail.json"


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


def _get_secret(account: str) -> str | None:
    if sys.platform == "darwin":
        try:
            return keyring.get_password(KEYRING_SERVICE, account)
        except KeyringError as error:
            raise CredentialStoreError("The native credential store is unavailable.") from error

    if sys.platform == "linux":
        result = _secret_tool("lookup", "service", KEYRING_SERVICE, "account", account)
        if result.returncode != 0:
            return None
        return result.stdout.removesuffix("\n")

    raise CredentialStoreError("No supported native credential store is available.")


def _set_secret(account: str, value: str) -> None:
    if sys.platform == "darwin":
        try:
            keyring.set_password(KEYRING_SERVICE, account, value)
        except KeyringError as error:
            raise CredentialStoreError("The native credential store is unavailable.") from error
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
        raise CredentialStoreError("Gmail OAuth configuration is not present in the native credential store.")
    try:
        return json.loads(value)
    except json.JSONDecodeError as error:
        raise CredentialStoreError("Gmail OAuth configuration in the native credential store is invalid.") from error


def migrate_legacy_files() -> bool:
    """Move legacy local OAuth files into the native credential store safely."""
    sources = ((CLIENT_ACCOUNT, LEGACY_CLIENT_FILE), (TOKEN_ACCOUNT, LEGACY_TOKEN_FILE))
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
    """Return valid Gmail OAuth credentials sourced exclusively from the OS keyring."""
    token_value = _get_secret(TOKEN_ACCOUNT)
    token_info = json.loads(token_value) if token_value else None
    creds = Credentials.from_authorized_user_info(token_info, SCOPES) if token_info else None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_config = _load_json_secret(CLIENT_ACCOUNT)
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            callback_port = int(os.environ.get("PI_EMAIL_OAUTH_PORT", "0"))
            open_browser = os.environ.get("PI_EMAIL_OAUTH_OPEN_BROWSER", "1") != "0"
            creds = flow.run_local_server(port=callback_port, open_browser=open_browser)
        _set_secret(TOKEN_ACCOUNT, creds.to_json())

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
        return 1
    except Exception:
        print("Authentication unavailable.", file=sys.stderr)
        return 1
    print("Authenticated with native credential storage.")
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

    try:
        service = get_service()
        print(f"Authenticated as {get_account_email(service)} using native credential storage.")
    except CredentialStoreError as error:
        print(f"Authentication unavailable: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
