#!/usr/bin/env python3
"""
AI Classification for GitHub Secrets Scan findings.

Reads a JSON findings file, spawns a pi agent with OpenAI Codex to
classify each finding as "normal/test" or "needs review", and outputs
a structured report.

Usage:
    python3 ai_classify.py <findings.json>
"""

import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

# Pi CLI command template
PI_CMD = ["pi", "--provider", "openai-codex", "--model", "gpt-5.4-mini",
          "--print", "--no-tools"]

CLASSIFICATION_SYSTEM_PROMPT = """You are a security classification expert. Your task is to analyze GitHub secrets scan findings and classify each one as either:

- ✅ NORMAL / TEST DATA: The finding is clearly test data, example code, placeholder, template scaffolding, documentation example, mock data, or test certificate. These are NOT real secrets.
- 🚨 NEEDS REVIEW: The finding could be a real secret leak in production code, configuration, or documentation.

For each finding, you must consider:
1. File path: is it in a test file (*.test.*, *.spec.*, test_*), template dir, docs, test cert dir?
2. Value: is it a test password like '123456', 'password', 'test', 'mock', 'fake'?
3. Context: is the surrounding code test/mock setup or production config?

Respond with ONLY a JSON object (no markdown, no code fences) where keys are finding indices (0, 1, 2, ...) and values are objects with:
- "verdict": "normal" or "review"
- "reason": short explanation (max 60 chars)

Example response format:
{"0":{"verdict":"normal","reason":"Test file with mock password '123456'"},"1":{"verdict":"review","reason":"Password in production config.js"}}

Be thorough and conservative — if unsure, classify as "review"."""  # noqa: E501


def run_pi(prompt_text, timeout=120):
    """Run pi agent with given prompt text, return stdout."""
    try:
        result = subprocess.run(
            PI_CMD + ["--system-prompt", CLASSIFICATION_SYSTEM_PROMPT],
            input=prompt_text,
            capture_output=True,
            text=True,
            errors='replace',
            timeout=timeout,
        )
        if result.returncode != 0:
            return None, result.stderr.strip()
        return result.stdout.strip(), None
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT"
    except FileNotFoundError:
        return None, "pi command not found. Is pi installed?"
    except Exception as e:
        return None, str(e)


def batch_findings(findings, batch_size=30):
    """Split findings into batches for AI processing."""
    batches = []
    for i in range(0, len(findings), batch_size):
        batch = []
        for j, f in enumerate(findings[i:i + batch_size]):
            entry = {
                "idx": i + j,
                "pattern": f.get("pattern", "?"),
                "severity": f.get("severity", "?"),
                "file": f.get("file", "?"),
                "line": f.get("line", "?"),
                "value": f.get("value_snippet", "")[:100],
                "repo": f.get("repo", "?"),
                "is_fork": f.get("is_fork", False),
            }
            batch.append(entry)
        batches.append((i, batch))
    return batches


def build_prompt(batch_id, batch_entries):
    """Build a prompt for a batch of findings."""
    lines = [f"Classify these {len(batch_entries)} findings (batch {batch_id}):"]
    for entry in batch_entries:
        fork_label = " [FORK]" if entry["is_fork"] else ""
        lines.append(
            f"\n--- Finding #{entry['idx']} ---"
            f"\nRepo: {entry['repo']}{fork_label}"
            f"\nFile: {entry['file']}:{entry['line']}"
            f"\nPattern: {entry['pattern']} ({entry['severity']})"
            f"\nValue: {entry['value']}"
        )
    lines.append(
        f"\n\nRespond with a JSON object mapping each finding index to "
        f'{{"verdict": "normal"|"review", "reason": "..."}}.'
    )
    return "\n".join(lines)


def parse_ai_response(response_text):
    """Parse the JSON response from pi agent."""
    if not response_text:
        return {}

    # Strip any markdown code fences if present
    text = response_text.strip()
    if text.startswith("```"):
        # Remove code fences
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def classify_findings(all_findings):
    """Classify all findings using pi agent with OpenAI Codex."""
    batches = batch_findings(all_findings, batch_size=30)
    all_verdicts = {}

    print(f"  📦 Splitting {len(all_findings)} findings into {len(batches)} batches...\n",
          file=sys.stderr)

    for batch_id, (start_idx, batch) in enumerate(batches):
        print(f"  🤖 Processing batch {batch_id + 1}/{len(batches)} "
              f"(findings {start_idx}-{start_idx + len(batch) - 1})...",
              file=sys.stderr, flush=True)

        prompt = build_prompt(batch_id, batch)
        response, error = run_pi(prompt, timeout=180)

        if error:
            print(f"    ❌ Error: {error}", file=sys.stderr)
            # Fallback: classify based on simple rules
            for entry in batch:
                all_verdicts[entry["idx"]] = fallback_classify(entry)
            continue

        classified = parse_ai_response(response)
        if not classified:
            print(f"    ⚠️  Could not parse AI response, using fallback",
                  file=sys.stderr)
            for entry in batch:
                all_verdicts[entry["idx"]] = fallback_classify(entry)
        else:
            matched = 0
            for entry in batch:
                idx = entry["idx"]
                if str(idx) in classified:
                    all_verdicts[idx] = classified[str(idx)]
                    matched += 1
                else:
                    all_verdicts[idx] = fallback_classify(entry)
            print(f"    ✅ Classified {matched}/{len(batch)} findings",
                  file=sys.stderr)

    return all_verdicts


def fallback_classify(entry):
    """Simple static fallback if AI is unavailable."""
    filepath = (entry.get("file", "") or "").lower()
    value = (entry.get("value", "") or "").lower()
    pattern = entry.get("pattern", "")

    # Test file
    test_indicators = [
        ".test.", ".spec.", "/test_", "/__tests__/",
        "test-", "-test.",
    ]
    if any(t in filepath for t in test_indicators):
        return {"verdict": "normal", "reason": "Test file"}

    # Template/generator
    if "/generators/" in filepath and "/templates/" in filepath:
        return {"verdict": "normal", "reason": "Template/scaffold code"}

    # Test cert
    if "/t/cert/" in filepath and pattern == "private_key":
        return {"verdict": "normal", "reason": "Test certificate"}

    # Common test values
    test_values = ["test", "mock", "fake", "123456", "password", "admin@123",
                   "secret123", "temp-password", "[redacted]", "no-api-key-needed"]
    if any(tv in value for tv in test_values):
        return {"verdict": "normal", "reason": "Test/placeholder value"}

    # Fork repos — often contain upstream test data
    if entry.get("is_fork", False):
        return {"verdict": "normal", "reason": "Upstream fork test data"}

    # Environment variables patterns ($VAR)
    if "$" in value and any(c.isalpha() for c in value.split("$")[-1][:1]):
        return {"verdict": "normal", "reason": "Env variable ref, not a value"}

    # Default: needs review
    return {"verdict": "review", "reason": "Potential real secret"}


def print_classified_report(all_findings, verdicts, repos_scanned, clean_repos):
    """Print the AI-classified report."""
    severity_colors = {
        "critical": "🔴 CRITICAL",
        "high": "🟡 HIGH",
        "medium": "🔵 MEDIUM",
        "info": "⚪ INFO",
    }

    # Annotate findings with verdicts
    annotated = []
    for i, f in enumerate(all_findings):
        v = verdicts.get(i, {"verdict": "review", "reason": "Unknown"})
        f["ai_verdict"] = v["verdict"]
        f["ai_reason"] = v["reason"]
        annotated.append(f)

    # Separate by AI verdict
    needs_review = [f for f in annotated if f["ai_verdict"] == "review"]
    normal = [f for f in annotated if f["ai_verdict"] == "normal"]

    # Print header
    print("\n" + "=" * 62)
    print("  🤖 AI Classification Results")
    print("  Powered by OpenAI Codex (pi agent)")
    print("=" * 62)

    # Summary
    print(f"\n  📊 AI Classification Summary")
    print(f"  {'─' * 55}")
    print(f"  Total findings:           {len(annotated)}")
    print(f"  🚨 Needs review:          {len(needs_review)}")
    print(f"  ✅ Normal / Test data:    {len(normal)}")
    print(f"  Clean repos:             {len(clean_repos)}")
    print(f"  Repos with findings:     {len(repos_scanned)}")
    print()

    if not needs_review:
        print("  🎉 All findings appear to be normal test/example data!\n")

    # Print NEEDS REVIEW findings (most important)
    if needs_review:
        print(f"\n{'=' * 62}")
        print("  🚨 FINDINGS THAT NEED REVIEW")
        print(f"{'=' * 62}")

        by_severity = defaultdict(list)
        for f in needs_review:
            by_severity[f["severity"]].append(f)

        for severity in ["critical", "high", "medium", "info"]:
            findings = by_severity.get(severity, [])
            if not findings:
                continue
            label = severity_colors.get(severity, severity.upper())
            print(f"\n  {label} ({len(findings)} findings)")
            print(f"  {'─' * 55}")

            for f in findings:
                print(f"\n    📁 {f.get('repo', '?')}")
                file_short = f.get("file", "?")
                if "/" in file_short:
                    parts = file_short.split("/")
                    if len(parts) > 3:
                        file_short = "/".join(parts[-3:])
                commit_info = ""
                if f.get("commit"):
                    commit_info = f" (commit {f['commit']})"
                print(f"    📄 {file_short}:{f.get('line', '?')}{commit_info}")
                val = f.get("value_snippet", "")
                if len(val) > 80:
                    val = val[:77] + "..."
                print(f"    → {val}")
                print(f"    💡 AI says: {f['ai_reason']}")

    # Print NORMAL findings (summary only to avoid clutter)
    if normal:
        print(f"\n{'=' * 62}")
        print("  ✅ NORMAL / TEST DATA (filtered out)")
        print(f"{'=' * 62}")

        by_reason = defaultdict(int)
        for f in normal:
            by_reason[f["ai_reason"]] += 1

        for reason, count in sorted(by_reason.items(), key=lambda x: -x[1]):
            print(f"    • {reason}: {count} finding(s)")

        print(f"\n  💡 Tip: These are filtered as normal and can be ignored.")
        print(f"     Use --no-ai-classify to skip this step next time.")

    # Print updated stats
    print(f"\n  {'─' * 62}")
    print(f"  📊 Updated Summary")
    print(f"  {'─' * 62}")
    for severity in ["critical", "high", "medium", "info"]:
        total = len([f for f in all_findings if f["severity"] == severity])
        remaining = len([f for f in needs_review if f["severity"] == severity])
        if total > 0:
            label = severity_colors.get(severity, severity.upper())
            print(f"  {label}: {remaining} remaining (filtered {total - remaining} as normal)")

    print()


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="AI Classification for GitHub Secrets Scan findings"
    )
    parser.add_argument("--db", help="Path to mitigation database")
    parser.add_argument("--db-only", action="store_true",
                       help="Use mitigation DB only — no AI call. "
                            "Findings already in DB are skipped; "
                            "others are classified as 'review' by default.")
    parser.add_argument("json_path", nargs="?", help="Path to findings JSON file")
    args = parser.parse_args()

    if not args.json_path:
        parser.print_help()
        sys.exit(1)

    json_path = args.json_path
    if not os.path.exists(json_path):
        print(f"❌ File not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    # ── Mitigation DB ──
    db_path = args.db or os.path.join(os.path.dirname(__file__), "mitigation.db")
    mdb = MitigationDB(db_path)
    saved_to_db = False

    # Load findings
    with open(json_path) as f:
        report = json.load(f)

    all_findings = report.get("findings", [])
    repos_scanned = report.get("repos_scanned", [])
    clean_repos = report.get("clean_repos", [])

    if not all_findings:
        print("  ✅ No findings to classify.")
        mdb.close()
        return

    # ── Classification ──
    if args.db_only:
        # DB-only mode: no AI call, just use the mitigation database
        verdicts = {}
        for i, f in enumerate(all_findings):
            if mdb.is_mitigated(f):
                entry = mdb.lookup(f)
                verdicts[i] = {
                    "verdict": entry["verdict"],
                    "reason": f"From mitigation DB: {entry.get('comment', 'no comment')}",
                }
            else:
                verdicts[i] = {
                    "verdict": "review",
                    "reason": "Not in mitigation DB — needs human review",
                }
        print(f"  📦 DB-only mode: "
              f"{sum(1 for v in verdicts.values() if v['verdict'] == 'normal')} skipped via DB, "
              f"{sum(1 for v in verdicts.values() if v['verdict'] == 'review')} remain.\n",
              file=sys.stderr)
    else:
        # Full AI classification — pre-filter against DB to save tokens
        needs_ai = []
        pre_verdicts = {}
        for i, f in enumerate(all_findings):
            if mdb.is_mitigated(f):
                entry = mdb.lookup(f)
                pre_verdicts[i] = {
                    "verdict": entry["verdict"],
                    "reason": f"Mitigation DB: {entry.get('comment', 'known')}",
                }
            else:
                needs_ai.append((i, f))

        ai_count = len(needs_ai)
        db_skip_count = len(all_findings) - ai_count

        if ai_count == 0:
            print(f"  ✅ All {db_skip_count} findings already in mitigation DB — "
                  f"no AI call needed.", file=sys.stderr)
            verdicts = pre_verdicts
        else:
            print(f"  🎯 {db_skip_count} findings skipped (from DB), "
                  f"{ai_count} need AI classification...", file=sys.stderr)
            ai_indices = [idx for idx, _ in needs_ai]
            ai_findings = [f for _, f in needs_ai]
            ai_verdicts = classify_findings(ai_findings)

            verdicts = dict(pre_verdicts)
            for pos, (orig_idx, _) in enumerate(needs_ai):
                av = ai_verdicts.get(pos) or ai_verdicts.get(orig_idx)
                if av:
                    verdicts[orig_idx] = av
                else:
                    verdicts[orig_idx] = {"verdict": "review", "reason": "AI failed"}

        # ── Auto-store normal findings into mitigation DB ──
        saved_count = 0
        for i, f in enumerate(all_findings):
            v = verdicts.get(i, {"verdict": "review"})
            if v["verdict"] == "normal" and not mdb.is_mitigated(f):
                mdb.add(f, "normal", v.get("reason", "AI classified as normal"))
                saved_count += 1
                saved_to_db = True

        if saved_count > 0:
            print(f"  💾 Auto-stored {saved_count} normal finding(s) into mitigation DB.\n",
                  file=sys.stderr)

    # Print report
    print_classified_report(all_findings, verdicts, repos_scanned, clean_repos)

    # Save annotated report
    annotated = []
    for i, f in enumerate(all_findings):
        v = verdicts.get(i, {"verdict": "review", "reason": "Unknown"})
        f["ai_verdict"] = v["verdict"]
        f["ai_reason"] = v["reason"]
        annotated.append(f)

    output_path = json_path.replace(".json", "_classified.json")
    report["findings"] = annotated
    report["ai_classification"] = {
        "model": "gpt-5.4-mini (via pi agent)",
        "provider": "openai-codex",
        "total_classified": len(annotated),
        "needs_review": len([f for f in annotated if f["ai_verdict"] == "review"]),
        "normal": len([f for f in annotated if f["ai_verdict"] == "normal"]),
    }
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"  📄 AI-classified report saved to: {output_path}\n", file=sys.stderr)

    mdb.close()


if __name__ == "__main__":
    main()
