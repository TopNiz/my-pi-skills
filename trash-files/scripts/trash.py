#!/usr/bin/env python3
"""Private skill-local trash with explicit, non-overwriting restores."""

import argparse
import ctypes
import datetime as dt
import errno
import fcntl
import json
import os
from pathlib import Path
import stat
import sys
import uuid
from contextlib import contextmanager

SKILL_DIR = Path(__file__).resolve().parents[1]
STORE = SKILL_DIR / ".trash"


def timestamp():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def exists(path):
    return os.path.lexists(path)


def absolute_leaf(path):
    """Resolve parent aliases, but preserve a final symlink as the item itself."""
    path = Path(os.path.abspath(os.path.expanduser(os.fspath(path))))
    return path.parent.resolve() / path.name


def rename_exclusive(source, destination):
    """Atomic same-filesystem move that never replaces an existing destination."""
    library = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source)
    destination_bytes = os.fsencode(destination)
    if sys.platform == "darwin":
        move = library.renamex_np
        move.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        move.restype = ctypes.c_int
        result = move(source_bytes, destination_bytes, 0x00000004)  # RENAME_EXCL
    elif sys.platform.startswith("linux") and hasattr(library, "renameat2"):
        move = library.renameat2
        move.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                         ctypes.c_char_p, ctypes.c_uint]
        move.restype = ctypes.c_int
        result = move(-100, source_bytes, -100, destination_bytes, 1)  # NOREPLACE
    else:
        raise RuntimeError("This platform has no supported exclusive move API.")
    if result != 0:
        error = ctypes.get_errno()
        if error == errno.EXDEV:
            raise RuntimeError(
                "Different filesystems: nothing moved. Automatic copy/delete is disabled."
            )
        raise OSError(error, os.strerror(error), os.fspath(destination))


class Trash:
    def __init__(self, root=STORE):
        self.root = Path(root).absolute()

    @contextmanager
    def locked(self):
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = self.root.lstat()
        if not stat.S_ISDIR(info.st_mode) or self.root.is_symlink():
            raise RuntimeError("Trash storage must be a real directory, not a symlink.")
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise RuntimeError("Trash storage must belong to this user with mode 0700.")
        flags = os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW
        descriptor = os.open(self.root / ".lock", flags, 0o600)
        with os.fdopen(descriptor, "r+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def entry(self, entry_id):
        parts = entry_id.split("-", 1)
        if (len(parts) != 2 or len(parts[0]) != 8 or not parts[0].isdigit()
                or len(parts[1]) != 32
                or any(c not in "0123456789abcdef" for c in parts[1])):
            raise ValueError("Invalid trash ID.")
        entry = self.root / entry_id
        if entry.is_symlink() or not entry.is_dir():
            raise ValueError("Trash entry does not exist or is not a real directory.")
        return entry

    def save(self, entry, record):
        temporary = entry / (".record-" + uuid.uuid4().hex)
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            json.dump(record, stream, ensure_ascii=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, entry / "record.json")

    def load(self, entry):
        descriptor = os.open(entry / "record.json", os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor) as stream:
            record = json.load(stream)
        if (record.get("id") != entry.name
                or not isinstance(record.get("original"), str)
                or not Path(record["original"]).is_absolute()):
            raise ValueError("Invalid restore record.")
        return record

    def validate_source(self, path):
        source = absolute_leaf(path)
        if not exists(source):
            raise ValueError(f"Source does not exist: {source}")
        storage = self.root.resolve()
        if source == storage or source in storage.parents or storage in source.parents:
            raise ValueError("Cannot trash the storage directory, its parents, or its contents.")
        info = source.lstat()
        if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)
                or stat.S_ISLNK(info.st_mode)):
            raise ValueError("Only regular files, directories, and symlinks are supported.")
        if os.path.ismount(source):
            raise ValueError("Cannot trash a filesystem mount point.")
        if info.st_dev != self.root.stat().st_dev:
            raise ValueError("Source is on another filesystem; nothing moved.")
        return source

    def put(self, paths):
        with self.locked():
            sources = [self.validate_source(path) for path in paths]
            if len(set(sources)) != len(sources):
                raise ValueError("Duplicate source paths are not allowed.")
            for source in sources:
                if any(other in source.parents for other in sources if other != source):
                    raise ValueError("Do not specify both a directory and its contents.")
            for source in sources:
                entry_id = dt.datetime.now().strftime("%Y%m%d") + "-" + uuid.uuid4().hex
                entry = self.root / entry_id
                entry.mkdir(mode=0o700)
                record = {
                    "id": entry_id, "original": str(source),
                    "trashed_at": timestamp(), "state": "prepared",
                }
                # Write recovery information before moving the item.
                self.save(entry, record)
                try:
                    rename_exclusive(source, entry / "payload")
                except (OSError, RuntimeError):
                    record["state"] = "move_failed"
                    self.save(entry, record)
                    raise
                record["state"] = "stored"
                self.save(entry, record)
                print(json.dumps(record, ensure_ascii=True), flush=True)

    def list(self, include_restored=False):
        with self.locked():
            for entry in sorted(self.root.iterdir()):
                if entry.name.startswith("."):
                    continue
                try:
                    entry = self.entry(entry.name)
                    record = self.load(entry)
                    present = exists(entry / "payload")
                    if record.get("state") == "restored" and not include_restored:
                        continue
                    record["payload_present"] = present
                    record["original_present"] = exists(record["original"])
                    print(json.dumps(record, ensure_ascii=True))
                except (OSError, ValueError, TypeError) as error:
                    print(f"Cannot inspect entry {entry.name}: {error}", file=sys.stderr)

    def restore(self, entry_id, destination=None):
        with self.locked():
            entry = self.entry(entry_id)
            record = self.load(entry)
            payload = entry / "payload"
            if not exists(payload):
                raise ValueError("No stored payload. Inspect the record; do not guess or retry a move.")
            target = absolute_leaf(destination if destination is not None else record["original"])
            storage = self.root.resolve()
            if target == storage or target in storage.parents or storage in target.parents:
                raise ValueError("Restore destination cannot be inside trash or contain trash.")
            if exists(target):
                raise FileExistsError(f"Restore destination already exists: {target}")
            if not target.parent.is_dir():
                raise ValueError("Destination parent does not exist; choose an existing directory.")
            record["state"] = "restoring"
            record["restore_target"] = str(target)
            self.save(entry, record)
            # Exclusive move also protects against a destination created after the check.
            rename_exclusive(payload, target)
            record["state"] = "restored"
            record["restored_at"] = timestamp()
            self.save(entry, record)
            print(json.dumps(record, ensure_ascii=True), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    put = commands.add_parser("put", help="Move exact paths into private trash")
    put.add_argument("paths", nargs="+")
    listing = commands.add_parser("list", help="List restore records as JSON lines")
    listing.add_argument("--all", action="store_true", help="Include restored records")
    restore = commands.add_parser("restore", help="Restore one ID without overwriting")
    restore.add_argument("id")
    restore.add_argument("--to", help="Exact alternate destination path, not just a parent folder")
    args = parser.parse_args()
    trash = Trash()
    try:
        if args.command == "put":
            trash.put(args.paths)
        elif args.command == "list":
            trash.list(args.all)
        else:
            trash.restore(args.id, args.to)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
