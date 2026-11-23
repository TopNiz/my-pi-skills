#!/usr/bin/env python3
"""Account-bound Google Drive client with explicit writes and Trash-only removal."""
from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
LOCAL_CONFIG = ROOT / "config.local.json"
try:
    CONFIG = json.loads(LOCAL_CONFIG.read_text(encoding="utf-8")) if LOCAL_CONFIG.is_file() else {}
except Exception:
    print("Local configuration could not be loaded. Sensitive details were suppressed.", file=sys.stderr)
    raise SystemExit(1)
ACCOUNT = None
TOKEN_FILE = None
RUNTIME = Path(CONFIG.get("python_runtime", str(ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")))).expanduser()
SCOPE = "https://www.googleapis.com/auth/drive"
API = "https://www.googleapis.com/drive/v3/"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/"
FIELDS = "id,name,mimeType,parents,trashed,modifiedTime,size,webViewLink,capabilities(canEdit,canTrash,canUntrash)"
FOLDER = "application/vnd.google-apps.folder"

# Use this skill's virtual environment or an explicitly configured Python runtime.
if RUNTIME.is_file() and Path(sys.prefix).resolve() != RUNTIME.parent.parent.resolve():
    result = subprocess.run([str(RUNTIME), "-B", str(Path(__file__).resolve()), *sys.argv[1:]])
    raise SystemExit(result.returncode)

# OAuth callbacks and HTTP errors must never enter logs or tracebacks.
logging.disable(logging.CRITICAL)
try:
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("OAuth dependencies are unavailable. See SKILL.md for setup. Nothing was installed.", file=sys.stderr)
    raise SystemExit(1)


class SafeError(Exception):
    pass


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def item_id(value):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", value):
        raise argparse.ArgumentTypeError("Use an exact Drive item ID, not a URL or path.")
    return value


def api_request(session, method, path, *, params=None, body=None, data=None,
                headers=None, upload=False, stream=False):
    # No endpoint for deletion, permission removal, or emptying Trash is exposed.
    allowed = (method == "GET" and (path == "about" or path == "files" or
               re.fullmatch(r"files/[A-Za-z0-9_-]+(?:/export)?", path))) or (
        method in ("POST", "PATCH") and (
            (method == "POST" and path == "files") or
            (method == "PATCH" and re.fullmatch(r"files/[A-Za-z0-9_-]+", path))))
    if not allowed:
        raise SafeError("Blocked operation. Permanent deletion is not supported.")
    try:
        response = session.request(method, (UPLOAD if upload else API) + path,
                                   params=params, json=body, data=data, headers=headers,
                                   timeout=(10, 60), stream=stream)
    except Exception:
        raise SafeError("Google Drive request failed. Sensitive details were suppressed.") from None
    if not response.ok:
        code = response.status_code
        response.close()
        raise SafeError(f"Google Drive request failed (HTTP {code}). No fallback was attempted.")
    return response


def json_request(session, method, path, **kwargs):
    with api_request(session, method, path, **kwargs) as response:
        return response.json()


def verify_account(session):
    about = json_request(session, "GET", "about", params={"fields": "user(emailAddress)"})
    if about.get("user", {}).get("emailAddress", "").casefold() != ACCOUNT.casefold():
        raise SafeError("Account mismatch. Drive operations are blocked.")


def configured_path(value):
    path = Path(value).expanduser()
    path = (path if path.is_absolute() else ROOT / path).resolve()
    if not path.is_relative_to(ROOT):
        raise SafeError("Credential paths must stay inside this skill folder.")
    return path


def select_account(requested):
    global ACCOUNT, TOKEN_FILE
    account = requested or CONFIG.get("default_account")
    if not isinstance(account, str) or not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", account):
        raise SafeError("Configure a primary Google account address in config.local.json.")
    account = account.casefold()
    if account not in CONFIG.get("accounts", {}):
        raise SafeError("The selected account is not configured. No fallback account was used.")
    if not CONFIG.get("credentials_dir"):
        raise SafeError("Configure a private credentials_dir before authorization.")
    ACCOUNT = account
    TOKEN_FILE = configured_path(CONFIG["credentials_dir"]) / account / "token.drive.json"


def read_credentials():
    if TOKEN_FILE.is_symlink():
        raise SafeError("Credential symlinks are not supported.")
    if not TOKEN_FILE.exists():
        return None
    if os.name == "posix" and (TOKEN_FILE.stat().st_mode & 0o077):
        raise SafeError("Credential file permissions must be owner-only.")
    return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))


def store_credentials(credentials):
    base = TOKEN_FILE.parent.parent
    for directory in (base, TOKEN_FILE.parent):
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if directory.is_symlink():
            raise SafeError("Credential directory symlinks are not supported.")
        if os.name == "posix" and (directory.stat().st_mode & 0o077):
            raise SafeError("Credential directories must be owner-only. Existing permissions were not changed.")
    descriptor = os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        output.write(credentials.to_json())
    if not read_credentials():
        raise SafeError("Credential storage could not be verified.")


def connect():
    stored = read_credentials()
    if not stored:
        raise SafeError("Drive authorization is not stored. Run authorize and approve it in the browser.")
    credentials = Credentials.from_authorized_user_info(stored)
    if not credentials.has_scopes([SCOPE]):
        raise SafeError("The stored authorization does not include the required Drive permission.")
    session = AuthorizedSession(credentials)
    try:
        verify_account(session)
    except Exception:
        session.close()
        raise
    return session


def authorize():
    if read_credentials():
        raise SafeError("Drive authorization already exists. Replacement needs separate user approval.")
    account_config = CONFIG["accounts"][ACCOUNT]
    client_value = account_config.get("oauth_client_file") or CONFIG.get("oauth_client_file")
    if not client_value:
        raise SafeError("Configure a desktop OAuth client file for this account.")
    client_path = configured_path(client_value)
    client = json.loads(client_path.read_text(encoding="utf-8"))
    if "installed" not in client:
        raise SafeError("This workflow requires an existing desktop OAuth client.")
    flow = InstalledAppFlow.from_client_config(client, scopes=[SCOPE])
    print("Opening Google authorization in your browser. Approve the selected configured account.", flush=True)
    credentials = flow.run_local_server(
        host="127.0.0.1", port=0, open_browser=True, timeout_seconds=300,
        authorization_prompt_message=None,
        success_message="Google authorization received. You can close this tab and return to Pi.",
        login_hint=ACCOUNT, prompt="consent select_account", access_type="offline",
    )
    if not credentials.refresh_token or not credentials.has_scopes([SCOPE]):
        raise SafeError("Google did not grant the required reusable Drive authorization.")
    with AuthorizedSession(credentials) as session:
        verify_account(session)
    # Exclusive creation prevents replacement if credentials appeared during consent.
    store_credentials(credentials)
    print("Drive authorization succeeded. Separate credentials were saved to the configured private local directory.")


def metadata(session, file_id):
    return json_request(session, "GET", f"files/{file_id}", params={
        "fields": FIELDS, "supportsAllDrives": "true"})


def parent_folder(session, file_id):
    result = metadata(session, file_id)
    if result.get("mimeType") != FOLDER or result.get("trashed"):
        raise SafeError("The destination is not an active folder.")
    return result


def require_confirmation(args):
    if not args.execute:
        return False
    if args.confirm_account != ACCOUNT:
        raise SafeError("Execution requires --confirm-account with the configured account.")
    if hasattr(args, "id") and args.confirm_id != args.id:
        raise SafeError("Execution requires --confirm-id with the exact target item ID.")
    return True


def local_upload(path):
    source = Path(path).expanduser()
    if not source.is_file() or source.stat().st_size > 50 * 1024 * 1024:
        raise SafeError("Upload source must be an existing file no larger than 50 MiB.")
    return source, mimetypes.guess_type(source.name)[0] or "application/octet-stream"


def download(session, args):
    destination = Path(args.out).expanduser()
    if destination.exists() or destination.is_symlink() or not destination.parent.is_dir():
        raise SafeError("Download needs a new path in an existing folder. Overwriting is blocked.")
    info = metadata(session, args.id)
    if args.command == "download" and info.get("mimeType", "").startswith("application/vnd.google-apps."):
        raise SafeError("Google-native items require export; folders and shortcuts cannot be downloaded as files.")
    path = f"files/{args.id}" + ("/export" if args.command == "export" else "")
    params = {"mimeType": args.mime} if args.command == "export" else {"alt": "media", "supportsAllDrives": "true"}
    with api_request(session, "GET", path, params=params, stream=True) as response:
        # Exclusive creation prevents races and accidental replacement.
        with destination.open("xb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                output.write(chunk)
    emit({"saved": str(destination), "source_id": args.id})


def write_operation(session, args):
    execute = require_confirmation(args)
    target = metadata(session, args.id) if hasattr(args, "id") else None
    preview = {"operation": args.command, "dry_run": not execute, "account": ACCOUNT}
    if target:
        preview["target"] = target
    if hasattr(args, "parent"):
        preview["destination"] = parent_folder(session, args.parent)
    if hasattr(args, "name"):
        preview["new_name"] = args.name
    source = mime = None
    if args.command in ("upload", "update"):
        source, mime = local_upload(args.path)
        preview["source"] = str(source)
    if args.command == "update" and target.get("mimeType", "").startswith("application/vnd.google-apps."):
        raise SafeError("Content replacement of Google-native items is not supported.")
    if args.command == "trash":
        preview["folder_contents_affected"] = target.get("mimeType") == FOLDER
        preview["warning"] = "Google normally permanently deletes items after 30 days in Trash."
        if target.get("trashed"):
            raise SafeError("The item is already in Trash.")
        if not target.get("capabilities", {}).get("canTrash", False):
            raise SafeError("Google does not permit moving this item to Trash. No fallback is allowed.")
    if args.command == "restore":
        if not target.get("trashed") or not target.get("capabilities", {}).get("canUntrash", False):
            raise SafeError("This item cannot be restored by this account.")
    if args.command == "move" and target.get("mimeType") == FOLDER:
        preview["folder_contents_affected"] = True
    if not execute:
        emit(preview)
        return
    params = {"fields": FIELDS, "supportsAllDrives": "true"}
    if args.command == "mkdir":
        result = json_request(session, "POST", "files", params=params,
                              body={"name": args.name, "mimeType": FOLDER, "parents": [args.parent]})
    elif args.command == "upload":
        boundary = "drive_" + uuid.uuid4().hex
        meta = json.dumps({"name": args.name or source.name, "parents": [args.parent]}).encode()
        data = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode()
                + meta + f"\r\n--{boundary}\r\nContent-Type: {mime}\r\n\r\n".encode()
                + source.read_bytes() + f"\r\n--{boundary}--\r\n".encode())
        params["uploadType"] = "multipart"
        result = json_request(session, "POST", "files", upload=True, params=params, data=data,
                              headers={"Content-Type": f"multipart/related; boundary={boundary}"})
    elif args.command == "update":
        params["uploadType"] = "media"
        result = json_request(session, "PATCH", f"files/{args.id}", upload=True, params=params,
                              data=source.read_bytes(), headers={"Content-Type": mime})
    else:
        body = {}
        if args.command == "rename":
            body["name"] = args.name
        elif args.command == "move":
            params["addParents"] = args.parent
            old = [p for p in target.get("parents", []) if p != args.parent]
            if old:
                params["removeParents"] = ",".join(old)
        else:
            body["trashed"] = args.command == "trash"
        result = json_request(session, "PATCH", f"files/{args.id}", params=params, body=body)
    if args.command in ("trash", "restore") and result.get("trashed") != (args.command == "trash"):
        raise SafeError("The requested Trash state was not verified. Do not retry without inspection.")
    emit({"operation": args.command, "result": result})


def parser():
    main = argparse.ArgumentParser(description=__doc__)
    main.add_argument("--account", help="Configured primary Google account address")
    commands = main.add_subparsers(dest="command", required=True)
    commands.add_parser("authorize")
    commands.add_parser("status")
    listing = commands.add_parser("list")
    listing.add_argument("--parent", type=item_id)
    listing.add_argument("--trash", action="store_true")
    listing.add_argument("--limit", type=int, choices=range(1, 1001), default=50, metavar="1-1000")
    info = commands.add_parser("info")
    info.add_argument("id", type=item_id)
    for command in ("download", "export"):
        p = commands.add_parser(command)
        p.add_argument("id", type=item_id)
        p.add_argument("--out", required=True)
        if command == "export":
            p.add_argument("--mime", required=True)
    for command in ("mkdir", "upload", "update", "rename", "move", "trash", "restore"):
        p = commands.add_parser(command)
        if command in ("update", "rename", "move", "trash", "restore"):
            p.add_argument("id", type=item_id)
            p.add_argument("--confirm-id", type=item_id)
        if command in ("mkdir", "rename"):
            p.add_argument("name")
        if command in ("upload", "update"):
            p.add_argument("path")
        if command == "upload":
            p.add_argument("--name")
        if command in ("mkdir", "upload", "move"):
            p.add_argument("--parent", type=item_id, required=True)
        p.add_argument("--execute", action="store_true")
        p.add_argument("--confirm-account")
    return main


def main():
    os.umask(0o077)
    args = parser().parse_args()
    select_account(args.account)
    if args.command == "authorize":
        authorize()
        return
    with connect() as session:
        if args.command == "status":
            emit({"account": ACCOUNT, "drive_access": "verified", "permission": "full Drive",
                  "storage": "private local credential file", "permanent_deletion": "blocked by this skill"})
        elif args.command == "list":
            q = "trashed = " + ("true" if args.trash else "false")
            if args.parent:
                q += f" and '{args.parent}' in parents"
            params = {"q": q, "fields": f"nextPageToken,files({FIELDS})",
                      "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}
            items = []
            while len(items) < args.limit:
                params["pageSize"] = min(100, args.limit - len(items))
                page = json_request(session, "GET", "files", params=params)
                items.extend(page.get("files", []))
                cursor = page.get("nextPageToken")
                if not cursor:
                    break
                params["pageToken"] = cursor
            emit({"files": items, "has_more": bool(cursor), "limit": args.limit})
        elif args.command == "info":
            emit(metadata(session, args.id))
        elif args.command in ("download", "export"):
            download(session, args)
        else:
            write_operation(session, args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Operation cancelled.", file=sys.stderr)
        raise SystemExit(130)
    except SafeError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
    except Exception:
        print("Operation failed. Sensitive details were suppressed. No fallback was attempted.", file=sys.stderr)
        raise SystemExit(1)
