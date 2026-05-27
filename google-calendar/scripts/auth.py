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
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/calendar",           # full read/write
    "https://www.googleapis.com/auth/calendar.events",    # events CRUD
]

SKILL_DIR        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
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
