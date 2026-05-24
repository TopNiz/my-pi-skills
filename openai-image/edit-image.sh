#!/usr/bin/env bash
# Edit an existing image using OpenAI's Image Edits API (multipart/form-data)
#
# Usage:
#   ./edit-image.sh input.jpg "edit description" [output.png] [model=gpt-image-1] [size=1024x1024] [quality=medium]
#
# Examples:
#   ./edit-image.sh photo.jpg "change background to dark orange, studio lighting" portrait.png
#   ./edit-image.sh selfie.jpg "remove background, replace with white studio backdrop" headshot.png
#
# Note: Uses POST /v1/images/edits with multipart/form-data (not JSON).

set -euo pipefail

INPUT_IMAGE="${1:?Error: input image is required}"
PROMPT="${2:?Error: edit prompt is required}"
OUTPUT="${3:-openai-image-edit-output.png}"
MODEL="${4:-gpt-image-1}"
SIZE="${5:-1024x1024}"
QUALITY="${6:-medium}"

if [ ! -f "$INPUT_IMAGE" ]; then
  echo "Error: Input image not found: $INPUT_IMAGE"
  exit 1
fi

# Read API key from pi's auth.json
AUTH_FILE="$HOME/.pi/agent/auth.json"
API_KEY=$(python3 -c "
import json
with open('$AUTH_FILE') as f:
    auth = json.load(f)
print(auth['openai']['key'])
" 2>/dev/null) || {
  echo "Error: Could not read OpenAI API key from $AUTH_FILE"
  exit 1
}

echo "🎨 Editing image with $MODEL..."
echo "   Input: $INPUT_IMAGE"
echo "   Prompt: ${PROMPT:0:80}..."
echo "   Size: $SIZE | Quality: $QUALITY"
echo "   Output: $OUTPUT"

RESPONSE=$(curl -s --max-time 300 https://api.openai.com/v1/images/edits \
  -H "Authorization: Bearer $API_KEY" \
  -F "model=$MODEL" \
  -F "image=@$INPUT_IMAGE" \
  -F "prompt=$PROMPT" \
  -F "size=$SIZE" \
  -F "quality=$QUALITY")

echo "$RESPONSE" | python3 -c "
import json, base64, sys
data = json.load(sys.stdin)
if 'data' in data and len(data['data']) > 0:
    img_b64 = data['data'][0].get('b64_json')
    if img_b64:
        with open('$OUTPUT', 'wb') as f:
            f.write(base64.b64decode(img_b64))
        print(f'✅ Edited image saved to $OUTPUT')
        from PIL import Image
        img = Image.open('$OUTPUT')
        print(f'   Dimensions: {img.size[0]}x{img.size[1]}')
        print(f'   Tokens: {data.get(\"usage\", {}).get(\"total_tokens\", \"?\")}')
    else:
        print(f'⚠️  Got URL: {data[\"data\"][0].get(\"url\", \"unknown\")}')
elif 'error' in data:
    err = data['error']
    print(f'❌ API Error: {err.get(\"message\", \"unknown\")}')
    sys.exit(1)
else:
    print(f'❌ Unexpected: {json.dumps(data, indent=2)[:300]}')
    sys.exit(1)
"
