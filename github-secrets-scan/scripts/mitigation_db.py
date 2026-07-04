#!/usr/bin/env python3
"""
Mitigation Database for GitHub Secrets Scanner (SQLite).

Stores user-reviewed findings marked as "normal" (false positive / test data)
or "resolved" (real secret that has been remediated).

On subsequent scans, these findings are silently skipped — saving both
screen clutter and AI classification tokens.

The DB file is gitignored so your review decisions are local-only.

Usage (CLI):
    python3 mitigation_db.py list                          # List all entries
    python3 mitigation_db.py list --verdict normal         # Filter by verdict
    python3 mitigation_db.py remove <fingerprint>          # Remove entry
    python3 mitigation_db.py clear                         # Clear all entries
    python3 mitigation_db.py stats                         # Show DB statistics
    python3 mitigation_db.py vacuum                        # Reclaim space
"""

import argparse
import hashlib
import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Optional


# ──────────────────────────────────────────────
# Default path
# ──────────────────────────────────────────────
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "mitigation.db")


# ──────────────────────────────────────────────
# Core database class
# ──────────────────────────────────────────────

class MitigationDB:
    """Persistent store of user-reviewed findings backed by SQLite."""

    def __init__(self, db_path=None):
        self.path = db_path or DEFAULT_DB_PATH
        self._conn = None
        self._init_db()

    # ── Connection & schema ──

    def _connect(self):
        """Get or create the connection."""
        if self._conn is None:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            self._conn = sqlite3.connect(self.path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
        return self._conn

    def _init_db(self):
        """Ensure the schema exists."""
        conn = self._connect()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mitigations (
                fingerprint TEXT PRIMARY KEY,
                pattern     TEXT NOT NULL,
                value_snippet TEXT NOT NULL DEFAULT '',
                file        TEXT NOT NULL DEFAULT '',
                repo        TEXT NOT NULL DEFAULT '',
                verdict     TEXT NOT NULL CHECK(verdict IN ('normal', 'resolved')),
                comment     TEXT NOT NULL DEFAULT '',
                added_at    TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_mitigations_verdict
            ON mitigations(verdict)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_mitigations_repo
            ON mitigations(repo)
        """)

        # ── Repos table ──
        conn.execute("""
            CREATE TABLE IF NOT EXISTS repos (
                repo_full      TEXT PRIMARY KEY,
                owner          TEXT NOT NULL DEFAULT '',
                name           TEXT NOT NULL DEFAULT '',
                to_be_scanned  INTEGER NOT NULL DEFAULT 1,
                is_fork        INTEGER NOT NULL DEFAULT 0,
                description    TEXT NOT NULL DEFAULT '',
                added_at       TEXT NOT NULL,
                updated_at     TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_repos_to_be_scanned
            ON repos(to_be_scanned)
        """)
        conn.commit()

    def close(self):
        """Close the connection explicitly."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ── Fingerprinting ──

    @staticmethod
    def fingerprint(finding):
        """Create a stable, unique fingerprint for a finding.

        Uses pattern + truncated value snippet + file path + repo so that the
        same secret in the same file is recognised across scans, but
        different occurrences of the same pattern on different lines
        are still treated separately.
        """
        raw = (
            f"{finding.get('pattern', '?')}|"
            f"{finding.get('value_snippet', '')[:60]}|"
            f"{finding.get('file', '')}|"
            f"{finding.get('repo', '')}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]

    # ── Lookup ──

    def lookup(self, finding):
        """Check if a finding (dict) is in the DB. Returns entry dict or None."""
        fp = self.fingerprint(finding)
        return self._lookup_fp(fp)

    def _lookup_fp(self, fingerprint):
        """Lookup by fingerprint string. Returns dict or None."""
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM mitigations WHERE fingerprint = ?",
            (fingerprint,)
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def is_mitigated(self, finding):
        """Returns True if the finding is in the DB with verdict normal|resolved."""
        entry = self._lookup_fp(self.fingerprint(finding))
        return entry is not None and entry.get("verdict") in ("normal", "resolved")

    # ── CRUD ──

    def add(self, finding, verdict, comment=""):
        """Add (or update) a finding in the DB.

        Args:
            finding: Finding dict with at least pattern, value_snippet, file, repo.
            verdict: "normal" (false positive / test data) or "resolved" (remediated).
            comment: Optional human-readable note.
        """
        fp = self.fingerprint(finding)
        now = datetime.now(timezone.utc).isoformat()
        conn = self._connect()
        conn.execute("""
            INSERT INTO mitigations (fingerprint, pattern, value_snippet, file, repo,
                                     verdict, comment, added_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(fingerprint) DO UPDATE SET
                verdict     = excluded.verdict,
                comment     = excluded.comment,
                updated_at  = excluded.updated_at
        """, (
            fp,
            finding.get("pattern", ""),
            (finding.get("value_snippet", "") or "")[:80],
            finding.get("file", ""),
            finding.get("repo", ""),
            verdict,
            comment,
            now,
            now,
        ))
        conn.commit()
        return fp

    def bulk_add(self, findings, verdict, comment=""):
        """Add multiple findings at once (transactional, faster)."""
        conn = self._connect()
        now = datetime.now(timezone.utc).isoformat()
        rows = []
        for finding in findings:
            fp = self.fingerprint(finding)
            rows.append((
                fp,
                finding.get("pattern", ""),
                (finding.get("value_snippet", "") or "")[:80],
                finding.get("file", ""),
                finding.get("repo", ""),
                verdict,
                comment,
                now,
                now,
            ))
        conn.executemany("""
            INSERT INTO mitigations (fingerprint, pattern, value_snippet, file, repo,
                                     verdict, comment, added_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(fingerprint) DO UPDATE SET
                verdict     = excluded.verdict,
                comment     = excluded.comment,
                updated_at  = excluded.updated_at
        """, rows)
        conn.commit()
        return [r[0] for r in rows]  # return fingerprints

    def remove(self, fingerprint):
        """Remove a single entry by its fingerprint. Returns True on success."""
        conn = self._connect()
        cur = conn.execute("DELETE FROM mitigations WHERE fingerprint = ?", (fingerprint,))
        conn.commit()
        return cur.rowcount > 0

    def clear(self):
        """Remove all entries."""
        conn = self._connect()
        conn.execute("DELETE FROM mitigations")
        conn.commit()

    def vacuum(self):
        """Reclaim disk space."""
        conn = self._connect()
        conn.execute("VACUUM")
        conn.commit()

    # ── Repo tracking ──

    def get_repo_status(self, repo_full):
        """Get repo scan status. Returns dict with to_be_scanned, is_fork etc. or None."""
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM repos WHERE repo_full = ?",
            (repo_full,)
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def is_repo_known(self, repo_full):
        """Returns True if the repo is already in the DB."""
        return self.get_repo_status(repo_full) is not None

    def should_scan_repo(self, repo_full):
        """Returns True if repo is either unknown (first time) or marked to_be_scanned=1."""
        status = self.get_repo_status(repo_full)
        if status is None:
            return True  # unknown → ask on first encounter
        return status["to_be_scanned"] == 1

    def set_repo_scan_flag(self, repo_full, owner, name, to_be_scanned, is_fork=False, description=""):
        """Set (or update) the scan flag for a repo."""
        conn = self._connect()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute("""
            INSERT INTO repos (repo_full, owner, name, to_be_scanned, is_fork, description, added_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo_full) DO UPDATE SET
                to_be_scanned = excluded.to_be_scanned,
                description   = excluded.description,
                updated_at    = excluded.updated_at
        """, (repo_full, owner, name, 1 if to_be_scanned else 0, 1 if is_fork else 0, description, now, now))
        conn.commit()

    def set_repos_batch(self, repos_info):
        """Batch upsert repos. repos_info is list of dicts with repo_full, owner, name, to_be_scanned, is_fork, description."""
        conn = self._connect()
        now = datetime.now(timezone.utc).isoformat()
        rows = []
        for r in repos_info:
            rows.append((
                r["repo_full"],
                r.get("owner", ""),
                r.get("name", ""),
                1 if r.get("to_be_scanned", True) else 0,
                1 if r.get("is_fork", False) else 0,
                r.get("description", ""),
                now,
                now,
            ))
        conn.executemany("""
            INSERT INTO repos (repo_full, owner, name, to_be_scanned, is_fork, description, added_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo_full) DO UPDATE SET
                to_be_scanned = excluded.to_be_scanned,
                description   = excluded.description,
                updated_at    = excluded.updated_at
        """, rows)
        conn.commit()

    def list_repos(self, to_be_scanned=None, is_fork=None, limit=200):
        """List repos, optionally filtered by scan flag and/or fork status."""
        conn = self._connect()
        conditions = []
        params = []
        if to_be_scanned is not None:
            conditions.append("to_be_scanned = ?")
            params.append(1 if to_be_scanned else 0)
        if is_fork is not None:
            conditions.append("is_fork = ?")
            params.append(1 if is_fork else 0)
        where = " AND ".join(conditions) if conditions else "1"
        rows = conn.execute(
            f"SELECT * FROM repos WHERE {where} ORDER BY repo_full ASC LIMIT ?",
            params + [limit]
        ).fetchall()
        return [dict(r) for r in rows]

    def reset_repos(self):
        """Delete all repo entries — will re-prompt on next scan."""
        conn = self._connect()
        conn.execute("DELETE FROM repos")
        conn.commit()

    def repo_stats(self):
        """Return repo table statistics."""
        conn = self._connect()
        total = conn.execute("SELECT COUNT(*) FROM repos").fetchone()[0]
        scan_yes = conn.execute(
            "SELECT COUNT(*) FROM repos WHERE to_be_scanned = 1"
        ).fetchone()[0]
        scan_no = conn.execute(
            "SELECT COUNT(*) FROM repos WHERE to_be_scanned = 0"
        ).fetchone()[0]
        forks = conn.execute(
            "SELECT COUNT(*) FROM repos WHERE is_fork = 1"
        ).fetchone()[0]
        unknown = conn.execute(
            "SELECT COUNT(*) FROM repos WHERE to_be_scanned = 1 AND is_fork = 0"
        ).fetchone()[0]
        return {
            "total": total,
            "to_be_scanned": scan_yes,
            "skipped": scan_no,
            "forks": forks,
            "active": unknown,
        }

    # ── Mitigation Queries ──

    def list_all(self, verdict=None, repo=None, limit=200):
        """Return entries, optionally filtered by verdict and/or repo."""
        conn = self._connect()
        conditions = []
        params = []
        if verdict:
            conditions.append("verdict = ?")
            params.append(verdict)
        if repo:
            conditions.append("repo = ?")
            params.append(repo)
        where = " AND ".join(conditions) if conditions else "1"
        rows = conn.execute(
            f"SELECT * FROM mitigations WHERE {where} ORDER BY added_at DESC LIMIT ?",
            params + [limit]
        ).fetchall()
        return [dict(r) for r in rows]

    def stats(self):
        """Return summary statistics."""
        conn = self._connect()
        total = conn.execute("SELECT COUNT(*) FROM mitigations").fetchone()[0]
        normal = conn.execute(
            "SELECT COUNT(*) FROM mitigations WHERE verdict = 'normal'"
        ).fetchone()[0]
        resolved = conn.execute(
            "SELECT COUNT(*) FROM mitigations WHERE verdict = 'resolved'"
        ).fetchone()[0]

        # Top repos from mitigations
        by_repo = {}
        rows = conn.execute(
            "SELECT repo, COUNT(*) as cnt FROM mitigations "
            "GROUP BY repo ORDER BY cnt DESC LIMIT 20"
        ).fetchall()
        for r in rows:
            repo_name = r["repo"] or "?"
            by_repo[repo_name] = r["cnt"]

        # Repo table stats
        repo_info = self.repo_stats()

        return {
            "total": total,
            "normal": normal,
            "resolved": resolved,
            "by_repo": by_repo,
            "repos": repo_info,
            "db_path": self.path,
        }


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def cli_main():
    parser = argparse.ArgumentParser(
        description="Manage the GitHub Secrets Scan mitigation database (SQLite)."
    )
    parser.add_argument(
        "--db", default=DEFAULT_DB_PATH,
        help=f"Path to mitigation DB (default: {DEFAULT_DB_PATH})"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list
    list_parser = subparsers.add_parser("list", help="List all entries")
    list_parser.add_argument("--verdict", choices=["normal", "resolved"],
                             help="Filter by verdict")
    list_parser.add_argument("--repo", help="Filter by repository")
    list_parser.add_argument("--limit", type=int, default=200,
                             help="Max entries to show (default: 200)")

    # remove
    rem_parser = subparsers.add_parser("remove", help="Remove an entry by fingerprint")
    rem_parser.add_argument("fingerprint", help="Fingerprint (20-char hex)")

    # clear
    subparsers.add_parser("clear", help="Remove ALL entries (irreversible)")

    # repos
    repos_parser = subparsers.add_parser("repos", help="List tracked repos and their scan flags")
    repos_parser.add_argument("--scanned", action="store_true",
                               help="Show only repos flagged to be scanned")
    repos_parser.add_argument("--skipped", action="store_true",
                               help="Show only repos flagged to skip")
    repos_parser.add_argument("--forks", action="store_true",
                               help="Show only forked repos")
    repos_parser.add_argument("--limit", type=int, default=200,
                               help="Max entries (default: 200)")

    # vacuum
    subparsers.add_parser("vacuum", help="Reclaim disk space")

    # stats
    subparsers.add_parser("stats", help="Show DB statistics")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    db = MitigationDB(args.db)

    if args.command == "list":
        entries = db.list_all(verdict=args.verdict, repo=args.repo, limit=args.limit)
        if not entries:
            print("  📭 Mitigation database is empty.")
            return
        print(f"\n  📋 Mitigation Database — {len(entries)} entries\n")
        for e in entries:
            verdict_icon = "✅" if e["verdict"] == "normal" else "🛡️"
            print(f"  {verdict_icon} [{e['verdict']}] {e['fingerprint']}")
            print(f"     Repo: {e.get('repo', '?')}")
            print(f"     File: {e.get('file', '?')}")
            print(f"     Pattern: {e.get('pattern', '?')}")
            print(f"     Value: {e.get('value_snippet', '')[:60]}")
            if e.get("comment"):
                print(f"     💬 {e['comment']}")
            print(f"     🕐 {e.get('added_at', '?')}")
            print()

    elif args.command == "remove":
        if db.remove(args.fingerprint):
            print(f"  ✅ Removed entry {args.fingerprint}")
        else:
            print(f"  ❌ Fingerprint not found: {args.fingerprint}")
            sys.exit(1)

    elif args.command == "clear":
        s = db.stats()
        if s["total"] == 0:
            print("  📭 Database already empty.")
            return
        confirm = input(
            f"  ⚠️  Clear ALL {s['total']} entries? This is irreversible. "
            f"Type 'yes': "
        )
        if confirm.lower() == "yes":
            db.clear()
            print("  ✅ Database cleared.")
        else:
            print("  ❌ Aborted.")

    elif args.command == "repos":
        to_be_scanned = None
        if args.scanned:
            to_be_scanned = True
        elif args.skipped:
            to_be_scanned = False
        is_fork = True if args.forks else None
        entries = db.list_repos(to_be_scanned=to_be_scanned, is_fork=is_fork, limit=args.limit)
        if not entries:
            print("  📭 No repos tracked yet. Run a scan to populate.")
            return
        print(f"\n  📋 Tracked Repos — {len(entries)} entries\n")
        for e in entries:
            flag = "✅" if e["to_be_scanned"] else "⏭️"
            fork = " (fork)" if e["is_fork"] else ""
            desc = ""
            if e.get("description"):
                d = e["description"]
                desc = f" — {d[:60]}{'…' if len(d) > 60 else ''}"
            print(f"  {flag} [{e['repo_full']}]{fork}{desc}")
        print()

    elif args.command == "vacuum":
        before = os.path.getsize(db.path) if os.path.exists(db.path) else 0
        db.vacuum()
        after = os.path.getsize(db.path) if os.path.exists(db.path) else 0
        saved = before - after
        print(f"  ✅ Database vacuumed: {_fmt_size(before)} → {_fmt_size(after)} "
              f"(saved {_fmt_size(saved)})")

    elif args.command == "stats":
        s = db.stats()
        print(f"\n  📊 Mitigation Database Statistics")
        print(f"  {'─' * 50}")
        print(f"  Database path:  {s['db_path']}")
        print(f"  Format:         SQLite")
        db_size = os.path.getsize(db.path) if os.path.exists(db.path) else 0
        print(f"  Size:           {_fmt_size(db_size)}")
        print()

        # Mitigations
        print(f"  🛡️  Mitigations")
        print(f"  {'─' * 50}")
        print(f"  Total entries:  {s['total']}")
        print(f"  ✅ Normal:       {s['normal']}")
        print(f"  🛡️  Resolved:    {s['resolved']}")
        if s["by_repo"]:
            print(f"\n  By repository:")
            for repo, count in s["by_repo"].items():
                print(f"    • {repo}: {count}")
        print()

        # Repos
        r = s.get("repos", {})
        print(f"  📁 Tracked Repos")
        print(f"  {'─' * 50}")
        print(f"  Total:          {r.get('total', 0)}")
        print(f"  ✅ To scan:      {r.get('to_be_scanned', 0)}")
        print(f"  ⏭️  Skipped:     {r.get('skipped', 0)}")
        print(f"  🍴 Forks:        {r.get('forks', 0)}")
        print()

    db.close()


def _fmt_size(n_bytes):
    """Human-readable file size."""
    for unit in ("B", "KB", "MB"):
        if n_bytes < 1024:
            return f"{n_bytes:.1f} {unit}"
        n_bytes /= 1024
    return f"{n_bytes:.1f} GB"


if __name__ == "__main__":
    cli_main()
