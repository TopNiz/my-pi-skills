#!/usr/bin/env bash
# Describe one or more images using pi + a vision model.
# Usage:
#   ./describe-image.sh image.png [image2.png ...]
#   ./describe-image.sh --provider openai-codex --model gpt-5.4 image.png
#   ./describe-image.sh --output-dir ./descriptions image.png
#
# Each image produces a <name>_description.md file next to it (or in --output-dir).

set -euo pipefail

# Defaults
PROVIDER="openai"
MODEL="gpt-4.1-mini"
OUTPUT_DIR=""

# Parse flags before positional args
POSITIONAL=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --provider)
      PROVIDER="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [--provider <provider>] [--model <model>] [--output-dir <dir>] <image1.png> [image2.png ...]"
      echo ""
      echo "Options:"
      echo "  --provider <name>   pi provider to use (default: openai)"
      echo "  --model <id>        vision model to use (default: gpt-4.1-mini)"
      echo "  --output-dir <dir>  where to write description files (default: same dir as each image)"
      echo ""
      echo "Examples:"
      echo "  $0 image.png"
      echo "  $0 --provider openai-codex --model gpt-5.4 image_01.png image_02.png"
      echo "  $0 --output-dir ./descriptions *.png"
      exit 0
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done

set -- "${POSITIONAL[@]}"

if [ $# -eq 0 ]; then
  echo "❌ Error: at least one image file is required."
  echo "Usage: $0 [--provider <provider>] [--model <model>] [--output-dir <dir>] <image1.png> [image2.png ...]"
  exit 1
fi

# Resolve pi path
PI_CMD=$(which pi 2>/dev/null || echo "$HOME/.nvm/versions/node/v24.11.0/bin/pi")

echo "🔍 Image Describer — Using $PROVIDER/$MODEL"
echo ""

DESCRIBE_PROMPT="Describe this image in great detail. Cover:
1. The overall content and what it shows
2. Layout and composition
3. All visible text (transcribed verbatim)
4. Visual elements, colors, typography, icons
5. The purpose / intended message of this image

Write the description in the same language as the image text.
Format the output as a clean Markdown document with sections."

for IMAGE in "$@"; do
  if [ ! -f "$IMAGE" ]; then
    echo "⚠️  Skipping: '$IMAGE' not found"
    continue
  fi

  # Determine output path
  BASENAME=$(basename "$IMAGE")
  NAME="${BASENAME%.*}"
  DIR=$(dirname "$IMAGE")

  if [ -n "$OUTPUT_DIR" ]; then
    mkdir -p "$OUTPUT_DIR"
    OUTPUT_FILE="${OUTPUT_DIR}/${NAME}_description.md"
  else
    OUTPUT_FILE="${DIR}/${NAME}_description.md"
  fi

  echo "📷  Processing: $BASENAME"
  echo "   → Output: $OUTPUT_FILE"

  # Call pi with the vision model (timeout after 120s)
  if ! $PI_CMD --provider "$PROVIDER" --model "$MODEL" --print -p "$DESCRIBE_PROMPT" "$IMAGE" > "$OUTPUT_FILE" 2>/dev/null; then
    echo "⚠️   Failed to describe $BASENAME. Check provider/model availability."
    rm -f "$OUTPUT_FILE"
    continue
  fi

  # Add a header to the output if not present
  if ! head -1 "$OUTPUT_FILE" | grep -q "^# "; then
    sed -i '' "1s/^/# Description de $BASENAME\n\n/" "$OUTPUT_FILE" 2>/dev/null || true
  fi

  # Count words
  if [ -f "$OUTPUT_FILE" ]; then
    WC=$(wc -c < "$OUTPUT_FILE" | tr -d ' ')
    echo "   ✅ Saved ($WC bytes)"
  fi
  echo ""
done

echo "✅ Done — described $# image(s)."
