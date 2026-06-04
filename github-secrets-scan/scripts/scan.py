#!/usr/bin/env python3
"""
GitHub Public Repository Secrets Scanner.

Scans public repositories for accidentally committed sensitive data:
passwords, API keys, tokens, SSH keys, email addresses, phone numbers,
connection strings, internal URLs, and more.

Usage:
    python3 scan.py [config.json] [options]

Options:
    --repos REPO [REPO ...]     Scan specific repos only (org/repo format)
    --account ACCOUNT           Scan a specific account only
    --no-commits                Skip commit history scan
    --no-files                  Skip file content scan
    --no-forks                  Exclude forked repositories
    --only PATTERN [PATTERN ..] Only scan specific pattern categories
    --skip REPO [REPO ...]      Skip specific repos
    --depth N                   Shallow clone depth (default: from config or 50)
    --json                      Output raw JSON
    -o FILE                     Output results to file
    --quiet                     Suppress progress output, show only findings
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

# Built-in patterns if patterns.md is not available
BUILTIN_PATTERNS = [
    {
        "name": "password_assignment",
        "severity": "critical",
        "contexts": ["files", "commits"],
        "regex": r'(?i)(?:password|passwd|pwd)\s*[=:]\s*[\'"][^\'"\n]{4,}[\'"]',
        "fp_contains": ["example", "placeholder", "password_hash", "hashed_password", "hash_password", "${TIKA", "${", "$(echo"],
    },
    {
        "name": "aws_access_key",
        "severity": "critical",
        "contexts": ["files", "commits"],
        "regex": r'AKIA[0-9A-Z]{16}',
        "fp_contains": ["example", "your_"],
    },
    {
        "name": "openai_api_key",
        "severity": "critical",
        "contexts": ["files", "commits"],
        "regex": r'sk-[A-Za-z0-9]{20,}',
        "fp_contains": ["example", "sk-your", "sk-xxxx"],
    },
    {
        "name": "google_api_key",
        "severity": "critical",
        "contexts": ["files", "commits"],
        "regex": r'AIza[0-9A-Za-z\-_]{35}',
        "fp_contains": ["example"],
    },
    {
        "name": "generic_api_key",
        "severity": "high",
        "contexts": ["files", "commits"],
        "regex": r'(?i)(?:api[_-]?key|api[_-]?secret|apikey)\s*[=:]\s*[\'"][^\'"]{8,}[\'"]',
        "fp_contains": ["example", "placeholder", "replace-with", "your_", "YOUR_"],
    },
    {
        "name": "github_token",
        "severity": "critical",
        "contexts": ["files", "commits"],
        "regex": r'(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}',
        "fp_contains": ["xxxx", "XXXX"],
    },
    {
        "name": "github_fine_grained_pat",
        "severity": "critical",
        "contexts": ["files", "commits"],
        "regex": r'github_pat_[A-Za-z0-9_]{22,}',
        "fp_contains": ["xxxx", "XXXX", "xxxxxxxx"],
    },
    {
        "name": "slack_token",
        "severity": "critical",
        "contexts": ["files", "commits"],
        "regex": r'xox[baprs]-[A-Za-z0-9-]{10,}',
        "fp_contains": [],
    },
    {
        "name": "jwt_token",
        "severity": "high",
        "contexts": ["files", "commits"],
        "regex": r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}',
        "fp_contains": ["eyJleGFtcGxl"],
    },
    {
        "name": "bearer_token",
        "severity": "high",
        "contexts": ["files", "commits"],
        "regex": r'(?i)Bearer\s+[A-Za-z0-9._\-+/]{20,}',
        "fp_contains": ["example", "sample"],
    },
    {
        "name": "private_key",
        "severity": "critical",
        "contexts": ["files", "commits"],
        "regex": r'-----BEGIN[ A-Z]+PRIVATE KEY-----',
        "fp_contains": ["example", "test_key", "TEST_PRIVATE"],
    },
    {
        "name": "ssh_public_key",
        "severity": "high",
        "contexts": ["files", "commits"],
        "regex": r'ssh-(rsa|ed25519|dss|ecdsa)\s+[A-Za-z0-9+/=]{50,}',
        "fp_contains": ["# authorized_keys"],
    },
    {
        "name": "db_connection_string",
        "severity": "critical",
        "contexts": ["files", "commits"],
        "regex": r'(postgresql|mysql|mongodb|redis|amqp|rabbitmq|rediss)://[^:]+:[^@]+@',
        "fp_contains": ["example", "localhost", "USER", "password_field"],
    },
    {
        "name": "url_credentials",
        "severity": "high",
        "contexts": ["files", "commits"],
        "regex": r'https?://[^:/\s]+:[^@\s]+@',
        "fp_contains": ["example.com"],
    },
    {
        "name": "email_address",
        "severity": "medium",
        "contexts": ["files", "commits"],
        "regex": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        "fp_domains": ["@example.com", "@domain.com", "@test.com", "@example.org", "@acm.org"],
        "fp_contains": ["user@", "your@", "test@", "email@", "you@"],
        "fp_domains_app": ["@nono-rent.fr", "@tourisfair.de", "@plania.io", "@upgrade-code.org"],
    },
    {
        "name": "phone_tunisia",
        "severity": "medium",
        "contexts": ["files", "commits"],
        "regex": r'(?:(?:\+216|00216)[1-9]\d{7}|0[1-9]\d{7})',
        "fp_contains": ["example", "12345678"],
    },
    {
        "name": "phone_france",
        "severity": "medium",
        "contexts": ["files", "commits"],
        "regex": r'(?:(?:\+33|0033)[1-9]\d{8}|0[1-9]\d{8})',
        "fp_contains": ["example", "12345678"],
    },
    {
        "name": "phone_us",
        "severity": "medium",
        "contexts": ["files", "commits"],
        "regex": r'(?:\+1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        "fp_contains": ["example", "1234567890"],
    },
    {
        "name": "aws_secret_key",
        "severity": "critical",
        "contexts": ["files", "commits"],
        "regex": r'(?i)aws[_-]?secret[_-]?access[_-]?key\s*[=:]\s*[\'"][A-Za-z0-9/+=]{40}[\'"]',
        "fp_contains": ["example"],
    },
    {
        "name": "internal_ip",
        "severity": "medium",
        "contexts": ["files", "commits"],
        "regex": r'(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})',
        "fp_contains": ["example", "x.x.x.x", "0.0.0.0"],
    },
    {
        "name": "localhost_reference",
        "severity": "info",
        "contexts": ["files", "commits"],
        "regex": r'https?://localhost(:\d+)?[/\s\)\"]',
        "fp_contains": [],
    },
    {
        "name": "internal_hostname",
        "severity": "medium",
        "contexts": ["files", "commits"],
        "regex": r'https?://[a-zA-Z0-9.-]+\.(local|internal|corp|lan)(?::\d+)?',
        "fp_contains": [],
    },
]


# Known false positive emails (npm maintainers, CI bots, etc.)
KNOWN_FP_EMAILS = {
    "ljharb@gmail.com", "sindresorhus@gmail.com", "substack@gmail.com",
    "i@izs.me", "mathias@qiwi.be", "thomas@nzgb.net", "paul@paulmillr.com",
}


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def load_config(path):
    """Load config.json."""
    if not os.path.exists(path):
        print(f"⚠️  Config not found at {path}, using defaults", file=sys.stderr)
        return {"accounts": {"active": ["TopNiz"], "list": {}}, "scan": {}}
    with open(path) as f:
        return json.load(f)


def load_patterns(patterns_path):
    """Try to load patterns from patterns.md (YAML-ish), fall back to builtins."""
    # For now we use built-in patterns directly.
    # In a future version, patterns.md could be parsed.
    return BUILTIN_PATTERNS


def is_false_positive(pattern, value, filepath=""):
    """Check if a match is a known false positive."""
    val_lower = value.lower()
    path_lower = filepath.lower()

    # Check fp_contains
    for fp in pattern.get("fp_contains", []):
        if fp.lower() in val_lower:
            return True

    # Check fp_domains (for email)
    for fp in pattern.get("fp_domains", []):
        if fp.lower() in val_lower:
            return True

    # Skip binary/package files
    if "/package.json" in path_lower and pattern["name"] == "email_address":
        return True  # npm maintainer emails

    if "/node_modules/" in path_lower:
        return True

    # Skip lock files
    if any(f in path_lower for f in ["package-lock.json", "yarn.lock", "pnpm-lock.yaml"]):
        return True

    # Skip .map files (source maps)
    if path_lower.endswith(".map"):
        return True

    # Known false positive emails (npm maintainers, etc.)
    if pattern["name"] == "email_address" and value in KNOWN_FP_EMAILS:
        return True
    
    # App-internal email domains (test/dev emails, not real leaks)
    if pattern["name"] == "email_address":
        for domain in pattern.get("fp_domains_app", []):
            if domain.lower() in val_lower:
                return True

    return False


def run_command(cmd, cwd=None, timeout=120, check=False):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except FileNotFoundError:
        return -2, "", "Command not found"


def get_public_repos(username):
    """Get list of public repos for a GitHub account using gh CLI."""
    cmd = ["gh", "repo", "list", username, "--limit", "300",
           "--json", "name,visibility,owner,isFork,description"]
    rc, stdout, stderr = run_command(cmd, timeout=30)
    if rc != 0:
        print(f"  ❌ Failed to list repos for {username}: {stderr.strip()}", file=sys.stderr)
        return []
    
    try:
        repos = json.loads(stdout)
    except json.JSONDecodeError:
        print(f"  ❌ Invalid JSON from gh for {username}", file=sys.stderr)
        return []
    
    # Filter to public repos only
    public = [r for r in repos if r.get("visibility", "").upper() == "PUBLIC"]
    return public


def shallow_clone(repo_full, dest_dir, depth=50):
    """Shallow clone a repo into dest_dir."""
    os.makedirs(dest_dir, exist_ok=True)
    repo_name = repo_full.replace("/", "_")
    target = os.path.join(dest_dir, repo_name)
    
    if os.path.exists(target):
        # Already exists — check if we can just fetch
        return target
    
    cmd = ["gh", "repo", "clone", repo_full, target, "--", 
           "--depth", str(depth), "--quiet"]
    rc, _, stderr = run_command(cmd, timeout=120)
    if rc != 0:
        print(f"    ❌ Clone failed: {stderr.strip()}", file=sys.stderr)
        return None
    return target


def scan_file(filepath, patterns, config):
    """Scan a single file for sensitive data patterns."""
    # Check file size
    try:
        size = os.path.getsize(filepath)
    except OSError:
        return []
    max_size = config.get("scan", {}).get("max_file_size_kb", 500) * 1024
    if size > max_size:
        return []
    
    # Check extension
    ext = os.path.splitext(filepath)[1].lower()
    ignored_exts = config.get("scan", {}).get("ignored_extensions", [])
    if ext in ignored_exts:
        return []
    
    # Check if in ignored directory
    parts = filepath.split(os.sep)
    ignored_dirs = config.get("scan", {}).get("ignored_dirs", [])
    if any(d in parts for d in ignored_dirs):
        return []
    
    # Check if ignored file
    filename = os.path.basename(filepath)
    ignored_files = config.get("scan", {}).get("ignored_files", [])
    if filename in ignored_files:
        return []
    # Check glob patterns
    ignored_glob = config.get("scan", {}).get("ignored_file_glob", [])
    for g in ignored_glob:
        if g.startswith("*.") and filename.endswith(g[1:]):
            return []
    
    # Read file
    try:
        with open(filepath, "r", errors="ignore") as f:
            content = f.read()
    except:
        return []
    
    findings = []
    for pattern in patterns:
        if "files" not in pattern.get("contexts", []):
            continue
        
        try:
            regex = re.compile(pattern["regex"])
        except re.error:
            continue
        
        for match in regex.finditer(content):
            value = match.group()
            if is_false_positive(pattern, value, filepath):
                continue
            
            # Get line number
            line_num = content[:match.start()].count("\n") + 1
            
            # Get surrounding context
            lines = content.split("\n")
            ctx_start = max(0, line_num - 3)
            ctx_end = min(len(lines), line_num + 2)
            context = "\n".join(lines[ctx_start:ctx_end])
            
            findings.append({
                "pattern": pattern["name"],
                "severity": pattern["severity"],
                "value_snippet": value[:120],
                "file": filepath,
                "line": line_num,
                "context": context,
            })
    
    return findings


def scan_commit_history(repo_path, patterns, config):
    """Scan git commit history for secrets in diffs."""
    cmd = ["git", "log", "--all", "-p"]
    rc, stdout, stderr = run_command(cmd, cwd=repo_path, timeout=120)
    if rc != 0:
        return []
    
    # Load ignored dirs/files from config
    ignored_dirs = config.get("scan", {}).get("ignored_dirs", [])
    ignored_files = config.get("scan", {}).get("ignored_files", [])
    ignored_exts = config.get("scan", {}).get("ignored_extensions", [])
    
    findings = []
    lines = stdout.split("\n")
    current_commit = "unknown"
    current_file = "unknown"
    
    def is_ignored_in_history(filepath):
        """Check if a file from commit history should be ignored."""
        parts = filepath.split("/")
        for d in ignored_dirs:
            if d in parts:
                return True
        fname = os.path.basename(filepath)
        if fname in ignored_files:
            return True
        # Check glob patterns
        for g in config.get("scan", {}).get("ignored_file_glob", []):
            if g.startswith("*.") and fname.endswith(g[1:]):
                return True
        ext = os.path.splitext(fname)[1].lower()
        if ext in ignored_exts:
            return True
        return False
    
    for line in lines:
        if line.startswith("commit "):
            current_commit = line.split()[1][:12]
        elif line.startswith("diff --git"):
            parts = line.split()
            if len(parts) >= 3:
                current_file = parts[2].replace("a/", "", 1)
        
        # Only scan added/modified lines (+ lines, excluding +++ header)
        if not line.startswith("+") or line.startswith("+++"):
            continue
        
        # Skip if file is in an ignored directory
        if is_ignored_in_history(current_file):
            continue
        
        line_content = line[1:]  # Remove the + prefix
        
        for pattern in patterns:
            if "commits" not in pattern.get("contexts", []):
                continue
            
            try:
                regex = re.compile(pattern["regex"])
            except re.error:
                continue
            
            for match in regex.finditer(line_content):
                value = match.group()
                if is_false_positive(pattern, value, current_file):
                    continue
                
                findings.append({
                    "pattern": pattern["name"],
                    "severity": pattern["severity"],
                    "value_snippet": value[:120],
                    "file": current_file,
                    "commit": current_commit,
                    "context": line_content[:200],
                })
    
    return findings


# ──────────────────────────────────────────────
# Reporting
# ──────────────────────────────────────────────

def deduplicate_findings(findings):
    """Remove duplicate findings (same pattern, same value, similar file)."""
    seen = set()
    unique = []
    for f in findings:
        key = (f["pattern"], f.get("value_snippet", "")[:60], f.get("file", ""))
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def severity_sort_key(f):
    """Sort by severity: critical > high > medium > info."""
    order = {"critical": 0, "high": 1, "medium": 2, "info": 3}
    return order.get(f.get("severity", "info"), 99)


def print_report(all_findings, repos_scanned, stats, args):
    """Print a formatted report of all findings."""
    if args.json:
        report = {
            "scan_time": datetime.now(timezone.utc).isoformat(),
            "repos_scanned": repos_scanned,
            "stats": stats,
            "findings": all_findings,
        }
        print(json.dumps(report, indent=2))
        return
    
    severity_colors = {
        "critical": "🔴 CRITICAL",
        "high": "🟡 HIGH",
        "medium": "🔵 MEDIUM",
        "info": "⚪ INFO",
    }
    
    # Group findings by severity
    by_severity = defaultdict(list)
    clean_repos = set(stats.get("clean_repos", []))
    repos_with_findings = set()
    for f in all_findings:
        by_severity[f["severity"]].append(f)
        repos_with_findings.add(f.get("repo", "unknown"))
    
    # Print header
    print()
    print("┌" + "─" * 57 + "┐")
    print(f"│ {'🔒 GitHub Secrets Scan Report':^55} │")
    print(f"│ {'Scanned: ' + datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'):^55} │")
    total_scanned = len(repos_scanned) if repos_scanned else stats.get("total", 0)
    print(f"│ {'Repos scanned: ' + str(total_scanned):^55} │")
    print(f"│ {'Total findings: ' + str(len(all_findings)):^55} │")
    print("└" + "─" * 57 + "┘")
    print()
    
    # Print by severity
    for severity in ["critical", "high", "medium", "info"]:
        findings = by_severity.get(severity, [])
        if not findings:
            continue
        
        label = severity_colors.get(severity, severity.upper())
        print(f"\n{label} ({len(findings)} findings)")
        print("  " + "─" * 55)
        
        # Group by repo
        by_repo = defaultdict(list)
        for f in findings:
            by_repo[f.get("repo", "unknown")].append(f)
        
        for repo_name in sorted(by_repo.keys()):
            repo_findings = by_repo[repo_name]
            print(f"\n  📁 {repo_name}")
            
            # Show up to 5 per pattern per repo to avoid flooding
            shown = 0
            for f in repo_findings:
                if shown >= 10:  # Limit per repo per severity group
                    remaining = len(repo_findings) - shown
                    if remaining > 0:
                        print(f"     ... and {remaining} more")
                    break
                
                file_short = f.get("file", "unknown")
                if "/" in file_short:
                    # Only show relative path
                    parts = file_short.split("/")
                    if len(parts) > 3:
                        file_short = "/".join(parts[-3:])
                
                pname = f.get("pattern", "?")
                commit_info = ""
                if f.get("commit"):
                    commit_info = f" (commit {f['commit']})"
                
                label = f"[{pname}]"
                print(f"    📄 {file_short}:{f.get('line', '?')}{commit_info}  {label}")
                
                val = f.get("value_snippet", "")
                if len(val) > 80:
                    val = val[:77] + "..."
                print(f"    → {val}")
                shown += 1
    
    # Print clean repos
    if clean_repos:
        print(f"\n✅ CLEAN repos ({len(clean_repos)})")
        print("  " + "─" * 55)
        for r in sorted(clean_repos):
            print(f"  • {r}")
    
    # Print summary
    print()
    print("📊 Summary")
    print("  " + "─" * 55)
    print(f"  Total repos scanned:  {stats.get('total', 0)}")
    print(f"  Repos with findings:  {len(repos_with_findings)}")
    print(f"  Clean repos:         {len(clean_repos)}")
    print(f"  Total findings:       {len(all_findings)}")
    for severity in ["critical", "high", "medium", "info"]:
        count = len(by_severity.get(severity, []))
        if count > 0:
            print(f"    {severity_colors[severity]}: {count}")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Scan GitHub public repos for leaked secrets"
    )
    parser.add_argument("config", nargs="?", default=DEFAULT_CONFIG_PATH,
                       help="Path to config.json")
    parser.add_argument("--repos", nargs="+", help="Specific repos to scan (org/repo)")
    parser.add_argument("--account", help="Scan a specific account only")
    parser.add_argument("--no-commits", action="store_true", help="Skip commit history scan")
    parser.add_argument("--no-files", action="store_true", help="Skip file content scan")
    parser.add_argument("--no-forks", action="store_true", help="Exclude forks")
    parser.add_argument("--only", nargs="+", help="Only scan specific patterns")
    parser.add_argument("--skip", nargs="+", help="Skip specific repos (org/repo)")
    parser.add_argument("--depth", type=int, default=50, help="Shallow clone depth")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("--quiet", action="store_true", help="Less verbose output")
    
    args = parser.parse_args()
    
    # Load config
    config = load_config(args.config)
    patterns = load_patterns(
        os.path.join(os.path.dirname(__file__), "..", "references", "patterns.md")
    )
    
    # Filter patterns if --only specified
    if args.only:
        patterns = [p for p in patterns if p["name"] in args.only]
        if not patterns:
            print("❌ No matching patterns found for --only filter", file=sys.stderr)
            sys.exit(1)
    
    # Determine which accounts to scan
    if args.account:
        active_accounts = [args.account]
    else:
        active_accounts = config.get("accounts", {}).get("active", ["TopNiz"])
    
    # Determine repos to skip
    skip_repos = set(args.skip or [])
    
    # Work directory
    work_dir = config.get("scan", {}).get("work_dir", "/tmp/github-secrets-scan")
    
    all_findings = []
    repos_scanned = []
    repo_stats = {"total": 0, "clean": 0, "with_findings": 0}
    clean_repos = []
    
    for account in active_accounts:
        if not args.quiet:
            print(f"\n{'='*60}")
            print(f"  📋 Account: {account}")
            print(f"{'='*60}")
        
        # Get public repos
        repos = get_public_repos(account)
        if not repos:
            if not args.quiet:
                print(f"  ⚠️  {account}: 0 public repos found — account may not exist or has no public repos", file=sys.stderr)
            continue
        
        # Filter: if --repos specified, only scan those
        if args.repos:
            repos = [r for r in repos if f"{account}/{r['name']}" in args.repos]
        
        # Filter: if --no-forks, exclude forks
        if args.no_forks:
            repos = [r for r in repos if not r.get("isFork", False)]
        
        # Filter: exclude account-specific excluded repos
        account_config = config.get("accounts", {}).get("list", {}).get(account, {})
        excluded = set(account_config.get("exclude_repos", []))
        repos = [r for r in repos if r["name"] not in excluded]
        repos = [r for r in repos if f"{account}/{r['name']}" not in skip_repos]
        
        if not repos:
            print(f"  ⚠️  No repos to scan after filtering", file=sys.stderr)
            continue
        
        if not args.quiet:
            print(f"  Found {len(repos)} public repos to scan\n")
        
        # Scan each repo
        for repo in repos:
            repo_full = f"{account}/{repo['name']}"
            is_fork = repo.get("isFork", False)
            fork_label = " (fork)" if is_fork else ""
            
            if not args.quiet:
                print(f"  🔄 Scanning {repo_full}{fork_label}...", end=" ", flush=True)
            
            depth = args.depth or account_config.get("depth", 50)
            clone_path = shallow_clone(repo_full, work_dir, depth=depth)
            
            if not clone_path:
                if not args.quiet:
                    print("❌ clone failed")
                continue
            
            repo_findings = []
            
            # File content scan
            if not args.no_files:
                for root, dirs, files in os.walk(clone_path):
                    # Skip .git
                    dirs[:] = [d for d in dirs if d != ".git"]
                    for fname in files:
                        fpath = os.path.join(root, fname)
                        file_findings = scan_file(fpath, patterns, config)
                        for ff in file_findings:
                            ff["repo"] = repo_full
                            ff["is_fork"] = is_fork
                            # Make file path relative
                            if fpath.startswith(clone_path):
                                ff["file"] = fpath[len(clone_path)+1:]
                        repo_findings.extend(file_findings)
            
            # Commit history scan
            if not args.no_commits:
                commit_findings = scan_commit_history(clone_path, patterns, config)
                for cf in commit_findings:
                    cf["repo"] = repo_full
                    cf["is_fork"] = is_fork
                repo_findings.extend(commit_findings)
            
            # Deduplicate
            repo_findings = deduplicate_findings(repo_findings)
            
            # Sort by severity
            repo_findings.sort(key=severity_sort_key)
            
            # Limit findings per repo
            max_per_repo = config.get("scan", {}).get("max_findings_per_repo", 50)
            repo_findings = repo_findings[:max_per_repo]
            
            if repo_findings:
                if not args.quiet:
                    print(f"🔍 {len(repo_findings)} finding(s)")
                repos_scanned.append(repo_full)
                all_findings.extend(repo_findings)
            else:
                if not args.quiet:
                    print("✅ clean")
                clean_repos.append(repo_full)
    
    # Stats
    stats = {
        "total": len(repos_scanned) + len(clean_repos),
        "clean_repos": clean_repos,
    }
    
    # Sort all findings by severity then repo
    all_findings.sort(key=lambda f: (severity_sort_key(f), f.get("repo", "")))
    
    # Output
    if args.output:
        report = {
            "scan_time": datetime.now(timezone.utc).isoformat(),
            "repos_scanned": repos_scanned,
            "clean_repos": clean_repos,
            "total_findings": len(all_findings),
            "findings": all_findings,
        }
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        if not args.quiet:
            print(f"\n📄 Report saved to: {args.output}")
    
    print_report(all_findings, repos_scanned, stats, args)


if __name__ == "__main__":
    main()
