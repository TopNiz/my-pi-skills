#!/usr/bin/env python3
"""
Google Calendar OAuth2 authentication helper.

First run: opens browser for user consent, saves token to ~/.agents/skills/google-calendar/token.json
Subsequent runs: refreshes token automatically.

Usage:
  python3 auth.py          # Authenticate and print "OK"
  python3 auth.py --check  # Check if already authenticated, exit 0/1
"""

import json
import os
import subprocess
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCOPES = [
    "https://www.googleapis.com/auth/calendar",           # full read/write
    "https://www.googleapis.com/auth/calendar.events",    # events CRUD
]

_VENV_PYTHON = os.path.join(
    SKILL_DIR,
    ".venv",
    "Scripts" if os.name == "nt" else "bin",
    "python.exe" if os.name == "nt" else "python",
)
_RUNNING_IN_VENV_ENV = "PI_GOOGLE_CALENDAR_IN_VENV"


def _force_utf8_stdio() -> None:
    """Make stdout/stderr UTF-8 on every platform.

    Windows consoles default to a legacy code page (cp1252 here), which raised
    UnicodeEncodeError when this script printed its status emoji.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):  # non-reconfigurable stream
            pass


def _venv_site_packages() -> str:
    """site-packages of the skill venv, for entry points we cannot re-exec."""
    if os.name == "nt":
        return os.path.join(SKILL_DIR, ".venv", "Lib", "site-packages")
    return os.path.join(
        SKILL_DIR,
        ".venv",
        "lib",
        f"python{sys.version_info.major}.{sys.version_info.minor}",
        "site-packages",
    )


def _ensure_skill_venv() -> None:
    """Re-exec under the uv-managed skill venv declared in ``pyproject.toml``.

    ``uv sync`` installs the Google API dependencies into ``<skill>/.venv``.
    Calling the scripts with any other interpreter would miss them, so
    transparently re-run under that venv when needed. If the venv is absent the
    scripts keep working with whatever interpreter is used.

    Never install these dependencies with ``pip install --target``: on Windows
    pip stages wheels in a ``mkdtemp()`` (mode 0o700) tree and moves them into
    place, which stamps an owner-only, inheritance-breaking DACL on every
    installed file and locks the dependencies out of non-owner accounts.
    """
    if os.environ.get(_RUNNING_IN_VENV_ENV) == "1" or not os.path.isfile(_VENV_PYTHON):
        return
    # Detect the venv via sys.prefix, not by comparing executable paths: on POSIX
    # .venv/bin/python is a symlink to the base interpreter, so a resolved-path
    # comparison reports "already inside the venv" and the bootstrap does nothing.
    if os.path.realpath(sys.prefix) == os.path.realpath(os.path.join(SKILL_DIR, ".venv")):
        return
    # subprocess (not os.execv) so stdout/stderr stay attached: on Windows
    # execv exits the parent before the child writes, losing piped output.
    # Only re-exec when sys.argv[0] is a real script we can replay; for piped
    # stdin (`python3 - < script`) or `-c` use the venv's packages in-process,
    # since replaying an exhausted stdin would silently run nothing.
    entry = sys.argv[0] if sys.argv else ""
    if entry and entry != "-" and os.path.isfile(entry):
        os.environ[_RUNNING_IN_VENV_ENV] = "1"
        raise SystemExit(
            subprocess.run([_VENV_PYTHON, *sys.argv], env=os.environ).returncode
        )

    site_packages = _venv_site_packages()
    if os.path.isdir(site_packages) and site_packages not in sys.path:
        sys.path.insert(0, site_packages)


_force_utf8_stdio()
_ensure_skill_venv()

from google.auth.transport.requests import Request  # noqa: E402
from google.oauth2.credentials import Credentials  # noqa: E402
from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402
from googleapiclient.discovery import build  # noqa: E402

CREDENTIALS_FILE = os.path.join(SKILL_DIR, "credentials.json")
TOKEN_FILE       = os.path.join(SKILL_DIR, "token.json")


def get_credentials():
    """Return valid Google OAuth2 credentials, refreshing or re-authorizing as needed."""
    creds = None

    if os.path.isfile(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.isfile(CREDENTIALS_FILE):
                print(f"❌ credentials.json not found at {CREDENTIALS_FILE}", file=sys.stderr)
                print("   Download it from Google Cloud Console → APIs & Services → Credentials", file=sys.stderr)
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0, open_browser=True)

        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        # Note: os.chmod only toggles the read-only attribute on Windows; it does
        # not restrict the DACL. Rely on the containing directory's permissions
        # (or move the token to the OS credential store, as email-manager does).
        os.chmod(TOKEN_FILE, 0o600)

    return creds


def get_service():
    """Return an authenticated Google Calendar API service."""
    creds = get_credentials()
    return build("calendar", "v3", credentials=creds)


if __name__ == "__main__":
    if "--check" in sys.argv:
        if os.path.isfile(TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
                if creds and creds.valid:
                    print("✅ Authenticated")
                    sys.exit(0)
                elif creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    print("✅ Token refreshed")
                    sys.exit(0)
            except Exception as e:
                print(f"❌ Token invalid: {e}")
                sys.exit(1)
        print("❌ Not authenticated")
        sys.exit(1)

    get_credentials()
    print("✅ Authenticated successfully. Token saved to:", TOKEN_FILE)
