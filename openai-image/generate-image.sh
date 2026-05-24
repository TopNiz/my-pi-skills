#!/usr/bin/env bash
# Generate an image using OpenAI's API (gpt-image models)
# Usage: ./generate-image.sh "prompt" [output.png] [model=gpt-image-1] [size=1536x1024] [quality=high]

set -euo pipefail

PROMPT="${1:?Error: prompt is required}"
OUTPUT="${2:-openai-image-output.png}"
MODEL="${3:-gpt-image-1}"
SIZE="${4:-1536x1024}"
QUALITY="${5:-high}"

# Read API key from pi's auth.json
AUTH_FILE="$HOME/.pi/agent/auth.json"
if [ ! -f "$AUTH_FILE" ]; then
  echo "Error: pi auth.json not found at $AUTH_FILE"
  echo "Make sure you have an OpenAI API key configured in pi."
  exit 1
fi

API_KEY=$(python3 -c "
import json
with open('$AUTH_FILE') as f:
    auth = json.load(f)
print(auth['openai']['key'])
" 2>/dev/null) || {
  echo "Error: Could not read OpenAI API key from $AUTH_FILE"
  echo "Make sure you have an 'openai' provider configured with a key."
  exit 1
}

echo "🎨 Generating image with $MODEL..."
echo "   Prompt: ${PROMPT:0:80}..."
echo "   Size: $SIZE | Quality: $QUALITY"
echo "   Output: $OUTPUT"

# Call the OpenAI API
RESPONSE=$(curl -s --max-time 300 https://api.openai.com/v1/images/generations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d "$(python3 -c "
import json
payload = {
    'model': '$MODEL',
    'prompt': '''$PROMPT''',
    'n': 1,
    'size': '$SIZE',
    'quality': '$QUALITY'
}
print(json.dumps(payload))
")")

# Check for errors and save the image
echo "$RESPONSE" | python3 -c "
import json, base64, sys
data = json.load(sys.stdin)
if 'data' in data and len(data['data']) > 0:
    img_b64 = data['data'][0]['b64_json']
    with open('$OUTPUT', 'wb') as f:
        f.write(base64.b64decode(img_b64))
    print('✅ Image saved to $OUTPUT')
    # Show dimensions
    from PIL import Image
    img = Image.open('$OUTPUT')
    print(f'   Dimensions: {img.size[0]}x{img.size[1]}')
elif 'error' in data:
    err = data['error']
    print(f'❌ API Error: {err.get(\"message\", \"unknown\")}')
    sys.exit(1)
else:
    print(f'❌ Unexpected response: {json.dumps(data, indent=2)[:300]}')
    sys.exit(1)
"
