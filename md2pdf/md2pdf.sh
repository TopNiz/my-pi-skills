#!/usr/bin/env bash
# ============================================================
# md2pdf.sh — Convertir un Markdown en PDF (pandoc + weasyprint)
# Skill global : ~/.agents/skills/md2pdf
#
# Usage :
#   ./md2pdf.sh fichier.md                  → fichier.pdf (à côté)
#   ./md2pdf.sh fichier.md sortie.pdf       → sortie.pdf
#   ./md2pdf.sh fichier.md sortie.pdf css   → sortie.pdf avec CSS personnalisée
#
# Pipeline : pandoc (MD → HTML fragment) + CSS + weasyprint (PDF)
# Polices : Arial Unicode MS + Apple Color Emoji (fallback emoji)
# Style par défaut : style.css (même dossier), remplaçable par le 3ᵉ argument
# Nettoyage : suppression des variation selectors U+FE0E/U+FE0F ajoutés par
#             pandoc 3.9 après certaines flèches (ex. ↔), non façonnables par
#             Pango/weasyprint avec Arial Unicode MS (.LastResort).
# ============================================================
set -euo pipefail

MD="${1:?Usage: md2pdf.sh fichier.md [sortie.pdf] [css]}"
OUT="${2:-${MD%.md}.pdf}"
CSS="${3:-}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "$CSS" ]]; then
  CSS="$DIR/style.css"
fi
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [[ ! -f "$MD" ]]; then
  echo "❌ Fichier introuvable : $MD" >&2
  exit 1
fi
if [[ ! -f "$CSS" ]]; then
  echo "❌ CSS introuvable : $CSS" >&2
  exit 1
fi

# 1. Markdown → HTML fragment (sans template pandoc, zéro warning CSS)
pandoc "$MD" -f markdown -t html5 -o "$TMP/body.html"

# 1b. Nettoyage variation selectors (pandoc 3.9 ajoute U+FE0E après ↔)
perl -CSD -i -pe 's/\x{FE0E}|\x{FE0F}//g' "$TMP/body.html"

# 2. Enveloppe HTML autonome avec le style du projet
{
  echo '<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">'
  echo '<style>'
  cat "$CSS"
  echo '</style></head><body>'
  cat "$TMP/body.html"
  echo '</body></html>'
} > "$TMP/doc.html"

# 3. HTML → PDF
weasyprint "$TMP/doc.html" "$OUT"

echo "✅ PDF généré : $OUT"
