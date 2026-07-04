#!/bin/bash
# ────────────────────────────────────────────────────────────
# GitHub Secrets Scan — Daily Report Script
# Runs the scanner for TopNiz, generates a PDF report,
# and emails an HTML body + PDF attachment to the user.
# ────────────────────────────────────────────────────────────

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPORTS_DIR="$SKILL_DIR/reports"
SCAN_SCRIPT="$SKILL_DIR/scripts/scan.py"
SEND_SCRIPT="$SKILL_DIR/scripts/send_email_report.py"
CONFIG="$SKILL_DIR/scripts/config.json"

# Recipient (can be changed)
TO_EMAIL="nizar.ayed@upgrade-code.org"

TIMESTAMP=$(date "+%Y-%m-%d_%H-%M-%S")
DATE_HUMAN=$(date "+%d/%m/%Y à %H:%M")

REPORT_BASENAME="github-secrets-scan_${TIMESTAMP}"
REPORT_JSON="${REPORTS_DIR}/${REPORT_BASENAME}.json"
REPORT_MD="${REPORTS_DIR}/${REPORT_BASENAME}.md"
REPORT_PDF="${REPORTS_DIR}/${REPORT_BASENAME}.pdf"
EMAIL_BODY="${REPORTS_DIR}/${REPORT_BASENAME}_email.html"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🔒 GitHub Secrets Scan — Daily Report"
echo "  Date : $DATE_HUMAN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Step 1: Run the scanner ──
echo ""
echo "📡 Scanning TopNiz public repositories..."
cd "$SKILL_DIR"

python3 "$SCAN_SCRIPT" "$CONFIG" \
    --account TopNiz \
    --json \
    -o "$REPORT_JSON" \
    2>/tmp/github_secrets_scan_stderr.log || true

# ── Step 1b: AI Classification ──
echo ""
echo "🤖 Running AI classification (OpenAI Codex)..."
CLASSIFY_SCRIPT="$SKILL_DIR/scripts/ai_classify.py"
REPORT_CLASSIFIED_JSON="${REPORT_JSON%.json}_classified.json"

if python3 "$CLASSIFY_SCRIPT" "$REPORT_JSON" 2>/tmp/github_secrets_ai_stderr.log; then
    echo "  ✅ AI classification terminée"
    # Use classified JSON for reporting
    REPORT_JSON="$REPORT_CLASSIFIED_JSON"
else
    echo "  ⚠️  AI classification a échoué, utilisation des résultats bruts"
    cat /tmp/github_secrets_ai_stderr.log
fi

# Extract stats (from classified or raw JSON)
TOTAL_FINDINGS=$(python3 -c "
import json
try:
    with open('$REPORT_JSON') as f:
        data = json.load(f)
    findings = data.get('findings', [])
    # If AI classified, count only 'review' verdicts
    if findings and 'ai_verdict' in findings[0]:
        review = [f for f in findings if f.get('ai_verdict') == 'review']
        print(len(review))
    else:
        print(len(findings))
except:
    print('0')
" 2>/dev/null || echo "0")

critical=$(python3 -c "
import json
try:
    with open('$REPORT_JSON') as f:
        data = json.load(f)
    findings = data.get('findings', [])
    if findings and 'ai_verdict' in findings[0]:
        cr = [f for f in findings if f.get('severity') == 'critical' and f.get('ai_verdict') == 'review']
    else:
        cr = [f for f in findings if f.get('severity') == 'critical']
    print(len(cr))
except:
    print('0')
" 2>/dev/null || echo "0")

high=$(python3 -c "
import json
with open('$REPORT_JSON') as f:
    data = json.load(f)
findings = data.get('findings', [])
if findings and 'ai_verdict' in findings[0]:
    h = [f for f in findings if f.get('severity') == 'high' and f.get('ai_verdict') == 'review']
else:
    h = [f for f in findings if f.get('severity') == 'high']
print(len(h))
" 2>/dev/null || echo "0")

medium=$(python3 -c "
import json
with open('$REPORT_JSON') as f:
    data = json.load(f)
findings = data.get('findings', [])
if findings and 'ai_verdict' in findings[0]:
    m = [f for f in findings if f.get('severity') == 'medium' and f.get('ai_verdict') == 'review']
else:
    m = [f for f in findings if f.get('severity') == 'medium']
print(len(m))
" 2>/dev/null || echo "0")

info=$(python3 -c "
import json
with open('$REPORT_JSON') as f:
    data = json.load(f)
findings = data.get('findings', [])
if findings and 'ai_verdict' in findings[0]:
    i = [f for f in findings if f.get('severity') == 'info' and f.get('ai_verdict') == 'review']
else:
    i = [f for f in findings if f.get('severity') == 'info']
print(len(i))
" 2>/dev/null || echo "0")

clean=$(python3 -c "
import json
with open('$REPORT_JSON') as f:
    data = json.load(f)
print(len(data.get('clean_repos', [])))
" 2>/dev/null || echo "0")

scanned=$(python3 -c "
import json
with open('$REPORT_JSON') as f:
    data = json.load(f)
print(len(data.get('repos_scanned', [])) + len(data.get('clean_repos', [])))
" 2>/dev/null || echo "0")

# Compute filtered stats (total raw findings)
TOTAL_RAW=$(python3 -c "
import json
with open('${REPORT_JSON%_classified.json}.json') as f:
    data = json.load(f)
print(len(data.get('findings', [])))
" 2>/dev/null || echo "$TOTAL_FINDINGS")

FILTERED=$((TOTAL_RAW - TOTAL_FINDINGS))
if [ "$FILTERED" -lt 0 ]; then FILTERED=0; fi

echo "  ✅ Scan terminé : $scanned repos scannés"
echo "     🔴 Critique: $critical (filtré) | 🟡 Élevé: $high | 🔵 Moyen: $medium | ⚪ Info: $info"
echo "     📊 $TOTAL_RAW trouvailles brutes → $TOTAL_FINDINGS après classification IA"
echo "     ✅ Clean repos: $clean"

# ── Step 2: Generate Markdown report (for PDF) ──
echo ""
echo "📝 Generating Markdown report (for PDF)..."

# If JSON report doesn't exist (scan crashed), create a minimal one
if [ ! -f "$REPORT_JSON" ]; then
    echo "  ⚠️  Rapport JSON introuvable, création d'un rapport minimal..."
    TIMESTAMP_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    cat > "$REPORT_JSON" << JSONEOF
{
  "scan_time": "${TIMESTAMP_ISO}",
  "repos_scanned": [],
  "clean_repos": [],
  "total_findings": 0,
  "findings": []
}
JSONEOF
    # Reset stats
    TOTAL_FINDINGS=0
    critical=0
    high=0
    medium=0
    info=0
    clean=0
    scanned=0
fi
cat > "$REPORT_MD" << MDEOF
---
title: "Rapport de Scan — Secrets GitHub"
date: "${DATE_HUMAN}"
---

# 🔒 GitHub Secrets Scan — Rapport Quotidien

**Date :** ${DATE_HUMAN}
**Compte scanné :** TopNiz
**Dépôts scannés :** ${scanned}
**Total des trouvailles :** ${TOTAL_FINDINGS}

---

## 📊 Résumé

| Catégorie | Nombre |
|-----------|:------:|
| 🔴 **Critique** | ${critical} |
| 🟡 **Élevé** | ${high} |
| 🔵 **Moyen** | ${medium} |
| ⚪ **Info** | ${info} |
| ✅ **Dépôts sains** | ${clean} |
| **Total** | **${scanned}** |

---

MDEOF

# Append findings
python3 -c "
import json, os

with open('$REPORT_JSON') as f:
    data = json.load(f)

findings = data.get('findings', [])
if not findings:
    print('✅ **Aucune trouvaille détectée.**', file=open('$REPORT_MD', 'a'))
else:
    # If AI-classified, filter to only "review" findings
    if findings and 'ai_verdict' in findings[0]:
        total_raw = len(findings)
        total_review = len([f for f in findings if f.get('ai_verdict') == 'review'])
        findings = [f for f in findings if f.get('ai_verdict') == 'review']
        print(f'🤖 **Classifié par IA (OpenAI Codex)** — {total_raw} trouvailles brutes → **{total_review} à vérifier**', file=open('$REPORT_MD', 'a'))
        print(f'', file=open('$REPORT_MD', 'a'))
    labels = {'critical': '🔴 Critique', 'high': '🟡 Élevé', 'medium': '🔵 Moyen', 'info': '⚪ Info'}
    for sev in ['critical', 'high', 'medium', 'info']:
        items = [f for f in findings if f.get('severity') == sev]
        if not items:
            continue
        print(f'\n## {labels.get(sev, sev)} ({len(items)})\n', file=open('$REPORT_MD', 'a'))
        by_repo = {}
        for f in items:
            by_repo.setdefault(f.get('repo', '?'), []).append(f)
        for repo in sorted(by_repo.keys()):
            print(f'### 📁 {repo}', file=open('$REPORT_MD', 'a'))
            for f in by_repo[repo]:
                fp = f.get('file', '?')
                ln = f.get('line', '?')
                pt = f.get('pattern', '?')
                cm = f.get('commit', '')
                vl = f.get('value_snippet', '')[:100]
                loc = f'{fp}:{ln}'
                if cm:
                    loc += f' (commit {cm[:8]})'
                print(f'- 📄 \`{loc}\`', file=open('$REPORT_MD', 'a'))
                print(f'  - **Pattern:** {pt}', file=open('$REPORT_MD', 'a'))
                print(f'  - \`{vl}\`', file=open('$REPORT_MD', 'a'))
                print(file=open('$REPORT_MD', 'a'))

    cr = data.get('clean_repos', [])
    if cr:
        print(f'\n## ✅ Dépôts sains ({len(cr)})\n', file=open('$REPORT_MD', 'a'))
        for r in sorted(cr):
            print(f'- {r}', file=open('$REPORT_MD', 'a'))
" 2>/dev/null

echo "  ✅ Markdown sauvegardé : $REPORT_MD"

# ── Step 3: Convert to PDF ──
echo ""
echo "📄 Converting to PDF..."

# Weasyprint + Apple Color Emoji font renders emojis properly in PDF.
# Create a temporary CSS that includes the emoji font fallback.
PDF_CSS="${REPORT_PDF%.pdf}.css"
cat > "$PDF_CSS" << 'CSSEOF'
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', 'Apple Color Emoji', 'Noto Color Emoji', sans-serif;
  font-size: 11pt;
  line-height: 1.5;
  color: #333;
  margin: 2cm;
}
h1 { font-size: 20pt; color: #1a1a2e; border-bottom: 2px solid #1a1a2e; padding-bottom: 6px; }
h2 { font-size: 16pt; color: #1a1a2e; margin-top: 24px; }
h3 { font-size: 13pt; color: #343a40; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; }
th, td { border: 1px solid #dee2e6; padding: 6px 10px; text-align: left; }
th { background: #1a1a2e; color: white; font-size: 10pt; }
tr:nth-child(even) { background: #f8f9fa; }
code {
  font-family: 'SF Mono', 'Menlo', 'Monaco', 'Courier New', monospace;
  background: #f5f5f5;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 10pt;
}
pre { background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 4px; padding: 10px; overflow-x: auto; }
strong { color: #1a1a2e; }
CSSEOF

# Use weasyprint as primary (supports emoji fonts)
pandoc "$REPORT_MD" -o "$REPORT_PDF" \
    --pdf-engine=weasyprint \
    --css "$PDF_CSS" \
    2>/tmp/github_secrets_pdf_stderr.log || {
        echo "  ⚠️ weasyprint failed, trying xelatex with text fallback..."
        # Create emoji-free version for xelatex
        REPORT_MD_CLEAN="${REPORT_MD%.md}_clean.md"
        python3 -c "
import re
with open('$REPORT_MD') as f:
    c = f.read()
replacements = {
    '🔒': '[LOCK]', '📊': '[STATS]', '🔴': '[CRITICAL]', '🟡': '[HIGH]',
    '🔵': '[MEDIUM]', '⚪': '[INFO]', '✅': '[OK]', '📄': '[FILE]',
    '📁': '[REPO]', '🔍': '[DETAIL]', '📝': '[DOC]', '📡': '[SCAN]',
    '📧': '[MAIL]', '🧹': '[CLEANUP]', '━━━': '---', '━': '-',
}
for em, tx in replacements.items():
    c = c.replace(em, tx)
c = re.sub(r'[\U0001F300-\U0001FFFF]', '', c)
with open('$REPORT_MD_CLEAN', 'w') as f:
    f.write(c)
"
        pandoc "$REPORT_MD_CLEAN" -o "$REPORT_PDF" \
            --pdf-engine=xelatex \
            -V colorlinks=true \
            -V linkcolor=blue \
            -V urlcolor=blue \
            -V geometry:margin=2cm \
            -V mainfont='Helvetica' \
            --pdf-engine-opt="-interaction=nonstopmode" \
            2>/tmp/github_secrets_pdf_stderr.log || {
                echo "  ❌ PDF generation failed"
                cat /tmp/github_secrets_pdf_stderr.log
                REPORT_PDF=""
            }
        rm -f "$REPORT_MD_CLEAN"
    }

# Clean up the temp CSS
rm -f "$PDF_CSS"

if [ -n "$REPORT_PDF" ] && [ -f "$REPORT_PDF" ]; then
    echo "  ✅ PDF sauvegardé : $REPORT_PDF"
else
    echo "  ⚠️  PDF non généré, envoi sans pièce jointe"
    REPORT_PDF=""
fi

# ── Step 4: Generate HTML email body ──
echo ""
echo "📧 Generating HTML email..."

# Build findings HTML via Python to handle escaping properly
python3 << PYEOF
import json

with open("$REPORT_JSON") as f:
    data = json.load(f)

findings = data.get("findings", [])
clean_repos = data.get("clean_repos", [])
total_raw = data.get("total_findings", len(findings))

# If AI-classified, filter to only "review" findings
has_ai_verdict = bool(findings and 'ai_verdict' in findings[0])
if has_ai_verdict:
    total_review = len([f for f in findings if f.get('ai_verdict') == 'review'])
    total_filtered = total_raw - total_review
    findings = [f for f in findings if f.get('ai_verdict') == 'review']
else:
    total_review = len(findings)
    total_filtered = 0

severity_cfg = {
    "critical": {"label": "Critique", "color": "#dc3545", "icon": "🔴"},
    "high":     {"label": "Élevé",   "color": "#ffc107", "icon": "🟡"},
    "medium":   {"label": "Moyen",   "color": "#0d6efd", "icon": "🔵"},
    "info":     {"label": "Info",    "color": "#6c757d", "icon": "⚪"},
}

counts = {"critical": 0, "high": 0, "medium": 0, "info": 0}
for f in findings:
    s = f.get("severity", "info")
    counts[s] = counts.get(s, 0) + 1

scanned = len(data.get("repos_scanned", [])) + len(clean_repos)

# -- Build summary table rows --
summary_rows = ""
for sev in ["critical", "high", "medium", "info"]:
    cfg = severity_cfg[sev]
    c = counts[sev]
    summary_rows += f"""<tr>
      <td style="padding:6px 12px;border:1px solid #dee2e6;text-align:center;font-size:18px;">{cfg["icon"]}</td>
      <td style="padding:6px 12px;border:1px solid #dee2e6;"><strong>{cfg["label"]}</strong></td>
      <td style="padding:6px 12px;border:1px solid #dee2e6;text-align:center;">
        <span style="display:inline-block;padding:2px 8px;border-radius:10px;color:#fff;font-weight:bold;background:{cfg['color']};">{c}</span>
      </td>
    </tr>"""

summary_rows += f"""<tr style="background:#f8f9fa;">
      <td style="padding:6px 12px;border:1px solid #dee2e6;text-align:center;font-size:18px;">✅</td>
      <td style="padding:6px 12px;border:1px solid #dee2e6;"><strong>Dépôts sains</strong></td>
      <td style="padding:6px 12px;border:1px solid #dee2e6;text-align:center;"><strong>{len(clean_repos)}</strong></td>
    </tr>"""

if has_ai_verdict:
    summary_rows += f"""<tr style="background:#e8f5e9;">
      <td style="padding:6px 12px;border:1px solid #dee2e6;text-align:center;font-size:18px;">🤖</td>
      <td style="padding:6px 12px;border:1px solid #dee2e6;"><strong>Filtrés (normaux/test)</strong></td>
      <td style="padding:6px 12px;border:1px solid #dee2e6;text-align:center;"><span style="display:inline-block;padding:2px 8px;border-radius:10px;color:#fff;font-weight:bold;background:#28a745;">{total_filtered}</span></td>
    </tr>"""

# -- Build findings detail --
findings_html = ""
if not findings:
    if has_ai_verdict:
        findings_html = """<tr><td colspan="4" style="padding:20px;text-align:center;color:#28a745;">🎉 Toutes les trouvailles ont été classifiées comme normales/test par l'IA. Aucun vrai secret détecté.</td></tr>"""
    else:
        findings_html = """<tr><td colspan="4" style="padding:20px;text-align:center;color:#6c757d;">✅ Aucune trouvaille détectée — tous les dépôts sont sains.</td></tr>"""
else:
    for sev in ["critical", "high", "medium", "info"]:
        items = [f for f in findings if f.get("severity") == sev]
        if not items:
            continue
        cfg = severity_cfg[sev]

        # Group by repo
        by_repo = {}
        for f in items:
            by_repo.setdefault(f.get("repo", "?"), []).append(f)

        for repo in sorted(by_repo.keys()):
            repo_items = by_repo[repo]
            first = True
            for f in repo_items:
                fp = f.get("file", "?")
                ln = f.get("line", "?")
                pt = f.get("pattern", "?")
                cm = f.get("commit", "")
                vl = f.get("value_snippet", "")[:80]
                fname = fp.split("/")[-1] if "/" in fp else fp
                loc = f"{fname}:{ln}"
                if cm:
                    loc += f" ({cm[:8]})"

                val_display = vl.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                repo_display = f"📁 {repo}" if first else ""

                badge = f"""<span style="display:inline-block;padding:1px 6px;border-radius:8px;color:#fff;font-size:11px;font-weight:bold;background:{cfg['color']};">{cfg['icon']} {cfg['label']}</span>"""

                findings_html += f"""<tr>
      <td style="padding:8px 12px;border:1px solid #dee2e6;vertical-align:top;">{repo_display}</td>
      <td style="padding:8px 12px;border:1px solid #dee2e6;vertical-align:top;white-space:nowrap;">{badge}</td>
      <td style="padding:8px 12px;border:1px solid #dee2e6;">
        <code style="background:#f5f5f5;padding:2px 4px;border-radius:3px;font-size:12px;">{loc}</code><br>
        <span style="color:#6c757d;font-size:12px;">{pt}</span>
      </td>
      <td style="padding:8px 12px;border:1px solid #dee2e6;">
        <code style="background:#fef3cd;padding:2px 4px;border-radius:3px;font-size:11px;word-break:break-all;">{val_display}</code>
      </td>
    </tr>"""
                first = False

    # Clean repos line
    if clean_repos:
        clean_list = ", ".join(sorted(clean_repos))
        findings_html += f"""<tr><td colspan="4" style="padding:10px 12px;border:1px solid #dee2e6;color:#28a745;">
          ✅ Dépôts sains ({len(clean_repos)}) : {clean_list}
        </td></tr>"""

# -- Assemble full HTML --
html = f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;">
<tr><td style="padding:20px 10px;">

  <!-- Container -->
  <table width="600" align="center" cellpadding="0" cellspacing="0"
         style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">

    <!-- Header -->
    <tr>
      <td style="padding:24px 28px;background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;text-align:center;">
        <h1 style="margin:0 0 6px;font-size:22px;font-weight:600;">🔒 Scan Secrets GitHub</h1>
        <p style="margin:0;font-size:14px;opacity:0.85;">Rapport quotidien — ${DATE_HUMAN}</p>
        <p style="margin:8px 0 0;font-size:12px;opacity:0.75;">🤖 Classifié par IA (OpenAI Codex) — ${FILTERED} trouvailles normales filtrées</p>
      </td>
    </tr>

    <!-- Meta info -->
    <tr>
      <td style="padding:16px 28px;background:#f8f9fa;border-bottom:1px solid #e9ecef;">
        <table width="100%">
          <tr>
            <td style="font-size:13px;color:#495057;"><strong>Compte :</strong> TopNiz</td>
            <td style="font-size:13px;color:#495057;text-align:right;"><strong>Dépôts scannés :</strong> {scanned}</td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- Summary -->
    <tr>
      <td style="padding:20px 28px;">
        <h2 style="margin:0 0 12px;font-size:18px;color:#1a1a2e;">📊 Résumé</h2>
        <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
          <thead>
            <tr style="background:#1a1a2e;color:#fff;">
              <th style="padding:8px 12px;text-align:center;width:40px;"></th>
              <th style="padding:8px 12px;text-align:left;">Catégorie</th>
              <th style="padding:8px 12px;text-align:center;width:80px;">Nombre</th>
            </tr>
          </thead>
          <tbody>
            {summary_rows}
          </tbody>
        </table>
      </td>
    </tr>

    <!-- Findings detail -->
    <tr>
      <td style="padding:0 28px 20px;">
        <h2 style="margin:0 0 12px;font-size:18px;color:#1a1a2e;">🔍 Détail des Trouvailles</h2>
        <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
          <thead>
            <tr style="background:#e9ecef;">
              <th style="padding:8px 12px;text-align:left;font-size:12px;text-transform:uppercase;color:#495057;">Dépôt</th>
              <th style="padding:8px 12px;text-align:left;font-size:12px;text-transform:uppercase;color:#495057;width:90px;">Sévérité</th>
              <th style="padding:8px 12px;text-align:left;font-size:12px;text-transform:uppercase;color:#495057;">Fichier</th>
              <th style="padding:8px 12px;text-align:left;font-size:12px;text-transform:uppercase;color:#495057;">Valeur</th>
            </tr>
          </thead>
          <tbody>
            {findings_html}
          </tbody>
        </table>
      </td>
    </tr>

    <!-- Footer -->
    <tr>
      <td style="padding:16px 28px;background:#f8f9fa;border-top:1px solid #e9ecef;text-align:center;">
        <p style="margin:0 0 4px;font-size:12px;color:#6c757d;">
          📄 Le rapport détaillé est joint en PDF.
        </p>
        <p style="margin:0;font-size:11px;color:#adb5bd;">
          Email automatique — Scanner GitHub Secrets
        </p>
      </td>
    </tr>

  </table>

</td></tr>
</table>

</body>
</html>"""

with open("$EMAIL_BODY", "w") as f:
    f.write(html)

print("✅ HTML email body generated")
PYEOF

echo "  ✅ Email body sauvegardé : $EMAIL_BODY"

# ── Step 5: Send email ──
AI_LABEL="🤖"
if [ "$FILTERED" -gt 0 ]; then
    AI_LABEL="🤖 IA"
    EMAIL_SUBJECT="🔒 Rapport Scan Secrets GitHub (IA) — ${DATE_HUMAN}"
else
    EMAIL_SUBJECT="🔒 Rapport Scan Secrets GitHub — ${DATE_HUMAN}"
fi
echo ""
echo "📤 Sending email..."

python3 "$SEND_SCRIPT" \
    "$TO_EMAIL" \
    "$EMAIL_SUBJECT" \
    "$EMAIL_BODY" \
    ${REPORT_PDF:+"$REPORT_PDF"} || {
        echo "  ❌ Échec d'envoi d'email"
        exit 1
    }

# ── Cleanup old reports (keep last 30 days) ──
echo ""
echo "🧹 Cleaning up old reports (keeping 30 days)..."
find "$REPORTS_DIR" -name "*.json" -mtime +30 -delete 2>/dev/null || true
find "$REPORTS_DIR" -name "*.md" -mtime +30 -delete 2>/dev/null || true
find "$REPORTS_DIR" -name "*.pdf" -mtime +30 -delete 2>/dev/null || true
find "$REPORTS_DIR" -name "*_email.html" -mtime +30 -delete 2>/dev/null || true

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Rapport terminé avec succès"
echo "  📄 PDF : $REPORT_PDF"
echo "  📧 Envoyé à : $TO_EMAIL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
