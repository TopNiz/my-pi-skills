#!/usr/bin/env bash
# Extract text/OCR content from files using a protected Apache Tika service.
# Usage:
#   ./extract-text.sh document.pdf scan.png
#   ./extract-text.sh --format markdown --output-dir ./text document.pdf
#   ./extract-text.sh --stdout document.pdf

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  set -a
  source "$ENV_FILE"
  set +a
fi

TIKA_URL="${TIKA_URL:-https://tika.codimeo.com}"
TIKA_USER="${TIKA_USER:-}"
TIKA_PASSWORD="${TIKA_PASSWORD:-}"
FORMAT="text"
OUTPUT_DIR=""
STDOUT=0
TIMEOUT=180

usage() {
  cat <<'EOF'
Usage: extract-text.sh [options] <file1> [file2 ...]

Extract text/OCR content from documents, PDFs, and images using Apache Tika.

Options:
  --format <text|markdown|html|json>  Output format (default: text)
  --output-dir <dir>                  Directory for output files (default: same as input)
  --stdout                            Print extracted content to stdout; only one input file allowed
  --url <url>                         Override TIKA_URL from .env
  --timeout <seconds>                 curl max time per file (default: 180)
  -h, --help                          Show this help

Environment (.env in this directory):
  TIKA_URL=https://tika.codimeo.com
  TIKA_USER=tika
  TIKA_PASSWORD=...

Examples:
  ./extract-text.sh invoice.pdf scan.png
  ./extract-text.sh --format markdown --output-dir ./out report.pdf
  ./extract-text.sh --stdout document.docx
EOF
}

POSITIONAL=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --format)
      FORMAT="${2:-}"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="${2:-}"
      shift 2
      ;;
    --stdout)
      STDOUT=1
      shift
      ;;
    --url)
      TIKA_URL="${2:-}"
      shift 2
      ;;
    --timeout)
      TIMEOUT="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      while [[ $# -gt 0 ]]; do
        POSITIONAL+=("$1")
        shift
      done
      ;;
    -*)
      echo "❌ Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done

set -- "${POSITIONAL[@]}"

if [ $# -eq 0 ]; then
  echo "❌ Error: at least one input file is required." >&2
  usage >&2
  exit 1
fi

if [ -z "$TIKA_USER" ] || [ -z "$TIKA_PASSWORD" ]; then
  echo "❌ Error: TIKA_USER and TIKA_PASSWORD must be set in $ENV_FILE or the environment." >&2
  echo "   Tip: cp $SCRIPT_DIR/.env.example $ENV_FILE && chmod 600 $ENV_FILE" >&2
  exit 1
fi

if [ "$STDOUT" -eq 1 ] && [ $# -ne 1 ]; then
  echo "❌ Error: --stdout can only be used with one input file." >&2
  exit 1
fi

case "$FORMAT" in
  text)
    ENDPOINT="/tika"
    ACCEPT="text/plain"
    EXT="txt"
    ;;
  markdown|md)
    ENDPOINT="/tika/md"
    ACCEPT="text/plain"
    EXT="md"
    ;;
  html)
    ENDPOINT="/tika"
    ACCEPT="text/html"
    EXT="html"
    ;;
  json)
    ENDPOINT="/tika"
    ACCEPT="application/json"
    EXT="json"
    ;;
  *)
    echo "❌ Unsupported format: $FORMAT" >&2
    echo "   Use: text, markdown, html, or json" >&2
    exit 1
    ;;
esac

TIKA_URL="${TIKA_URL%/}"
URL="$TIKA_URL$ENDPOINT"

if [ -n "$OUTPUT_DIR" ]; then
  mkdir -p "$OUTPUT_DIR"
fi

if [ "$STDOUT" -eq 0 ]; then
  echo "🔎 Extract Text — Using Apache Tika at $TIKA_URL ($FORMAT)"
  echo ""
fi

for INPUT in "$@"; do
  if [ ! -f "$INPUT" ]; then
    echo "⚠️  Skipping: '$INPUT' not found" >&2
    continue
  fi

  BASENAME="$(basename "$INPUT")"
  NAME="${BASENAME%.*}"
  DIR="$(dirname "$INPUT")"

  if [ "$STDOUT" -eq 1 ]; then
    curl -fsS \
      --max-time "$TIMEOUT" \
      -u "$TIKA_USER:$TIKA_PASSWORD" \
      -T "$INPUT" \
      -H "Accept: $ACCEPT" \
      -H "Content-Disposition: attachment; filename=\"$BASENAME\"" \
      "$URL"
    exit 0
  fi

  if [ -n "$OUTPUT_DIR" ]; then
    OUTPUT_FILE="$OUTPUT_DIR/$NAME.$EXT"
  else
    OUTPUT_FILE="$DIR/$NAME.$EXT"
  fi

  # Avoid overwriting the input when extracting from e.g. file.txt -> file.txt.
  if [ "$(cd "$(dirname "$OUTPUT_FILE")" && pwd)/$(basename "$OUTPUT_FILE")" = "$(cd "$DIR" && pwd)/$BASENAME" ]; then
    OUTPUT_FILE="${OUTPUT_FILE%.$EXT}_extracted.$EXT"
  fi

  TMP_FILE="$OUTPUT_FILE.tmp.$$"

  echo "📄  Processing: $BASENAME"
  echo "   → Output: $OUTPUT_FILE"

  if curl -fsS \
      --max-time "$TIMEOUT" \
      -u "$TIKA_USER:$TIKA_PASSWORD" \
      -T "$INPUT" \
      -H "Accept: $ACCEPT" \
      -H "Content-Disposition: attachment; filename=\"$BASENAME\"" \
      "$URL" > "$TMP_FILE"; then
    mv "$TMP_FILE" "$OUTPUT_FILE"
    BYTES=$(wc -c < "$OUTPUT_FILE" | tr -d ' ')
    echo "   ✅ Saved ($BYTES bytes)"
  else
    rm -f "$TMP_FILE"
    echo "   ⚠️  Failed to extract text from $BASENAME" >&2
  fi
  echo ""
done

if [ "$STDOUT" -eq 0 ]; then
  echo "✅ Done."
fi
