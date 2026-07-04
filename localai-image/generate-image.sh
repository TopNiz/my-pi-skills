#!/usr/bin/env bash
# Generate an image using the LocalAI service on pc-master.
# Usage: ./generate-image.sh "prompt" [output.png] [model=flux.2-klein-9b] [size=1024x1024]

set -euo pipefail

PROMPT="${1:?Error: prompt is required}"
OUTPUT="${2:-localai-image-output.png}"
MODEL="${3:-flux.2-klein-9b}"
SIZE="${4:-1024x1024}"
BASE_URL="${LOCALAI_IMAGE_BASE_URL:-http://192.168.0.7:11435}"
OVERWRITE="${LOCALAI_IMAGE_OVERWRITE:-0}"

if [ -e "$OUTPUT" ] && [ "$OVERWRITE" != "1" ]; then
  echo "Error: output file already exists: $OUTPUT"
  echo "Set LOCALAI_IMAGE_OVERWRITE=1 to overwrite intentionally."
  exit 1
fi

TMP_RESPONSE="$(mktemp)"
TMP_BODY="$(mktemp)"
cleanup() {
  rm -f "$TMP_RESPONSE" "$TMP_BODY"
}
trap cleanup EXIT

python3 - "$PROMPT" "$MODEL" "$SIZE" > "$TMP_BODY" <<'PY'
import json, sys
prompt, model, size = sys.argv[1:4]
print(json.dumps({
    "model": model,
    "prompt": prompt,
    "n": 1,
    "size": size,
}))
PY

echo "🎨 Generating local image with $MODEL..."
echo "   Server: $BASE_URL"
echo "   Prompt: ${PROMPT:0:100}$([ ${#PROMPT} -gt 100 ] && echo '...')"
echo "   Size: $SIZE"
echo "   Output: $OUTPUT"

HTTP_CODE=$(curl -sS --max-time "${LOCALAI_IMAGE_TIMEOUT:-600}" \
  -o "$TMP_RESPONSE" \
  -w '%{http_code}' \
  "$BASE_URL/v1/images/generations" \
  -H 'Content-Type: application/json' \
  --data-binary "@$TMP_BODY")

if [ "$HTTP_CODE" -lt 200 ] || [ "$HTTP_CODE" -ge 300 ]; then
  echo "❌ LocalAI request failed with HTTP $HTTP_CODE"
  python3 - "$TMP_RESPONSE" <<'PY'
import sys
text = open(sys.argv[1], 'r', errors='replace').read()
print(text[:1000])
PY
  exit 1
fi

python3 - "$TMP_RESPONSE" "$OUTPUT" "$BASE_URL" <<'PY'
import base64
import json
import os
import sys
import urllib.parse
import urllib.request

response_path, output, base_url = sys.argv[1:4]
with open(response_path, 'r', errors='replace') as f:
    data = json.load(f)

if 'error' in data:
    err = data['error']
    if isinstance(err, dict):
        msg = err.get('message') or json.dumps(err)
    else:
        msg = str(err)
    raise SystemExit(f"❌ LocalAI error: {msg}")

items = data.get('data') or []
if not items:
    raise SystemExit('❌ LocalAI response did not contain image data')

item = items[0]
if item.get('b64_json'):
    image_bytes = base64.b64decode(item['b64_json'])
elif item.get('url'):
    url = item['url']
    if url.startswith('/'):
        url = urllib.parse.urljoin(base_url.rstrip('/') + '/', url.lstrip('/'))
    elif url.startswith('http://localhost') or url.startswith('http://127.0.0.1'):
        parsed_base = urllib.parse.urlparse(base_url)
        parsed_url = urllib.parse.urlparse(url)
        url = urllib.parse.urlunparse(parsed_url._replace(scheme=parsed_base.scheme, netloc=parsed_base.netloc))
    with urllib.request.urlopen(url, timeout=300) as r:
        image_bytes = r.read()
else:
    raise SystemExit(f"❌ Unsupported image response keys: {', '.join(sorted(item.keys()))}")

out_dir = os.path.dirname(os.path.abspath(output))
if out_dir:
    os.makedirs(out_dir, exist_ok=True)
with open(output, 'wb') as f:
    f.write(image_bytes)

print(f"✅ Image saved to {output}")
try:
    from PIL import Image
    img = Image.open(output)
    print(f"   Dimensions: {img.size[0]}x{img.size[1]}")
except Exception:
    pass
PY
