---
name: localai-image
description: Generate images locally through the LocalAI service on pc-master.local / 192.168.0.7 port 11435. Uses the OpenAI-compatible /v1/images/generations endpoint and the flux.2-klein-9b model. Use when the user asks for local, private, or no-cloud image generation.
---

# LocalAI Image Generation

Generate images using the LocalAI service running on `pc-master.local` and reachable from this machine at `http://192.168.0.7:11435`.

## Verified service

- SSH host: `pc-master.local`
- Service host from this machine: `192.168.0.7`
- Port: `11435`
- API: OpenAI-compatible
- Endpoint: `/v1/images/generations`
- Available image model: `flux.2-klein-9b`

## Usage

```bash
/Users/nizarayed/.agents/skills/localai-image/generate-image.sh "prompt" [output.png] [model] [size]
```

Defaults:

- Model: `flux.2-klein-9b`
- Size: `1024x1024`
- Base URL: `http://192.168.0.7:11435`

Examples:

```bash
# Basic square image
/Users/nizarayed/.agents/skills/localai-image/generate-image.sh \
  "A watercolor illustration of a small robot gardening" robot-gardener.png

# Landscape style prompt; size support depends on the LocalAI backend
/Users/nizarayed/.agents/skills/localai-image/generate-image.sh \
  "A cinematic wide shot of mountains at sunrise, realistic" sunrise.png flux.2-klein-9b 1024x576
```

## Configuration

Override the server URL if needed:

```bash
LOCALAI_IMAGE_BASE_URL="http://192.168.0.7:11435" \
  /Users/nizarayed/.agents/skills/localai-image/generate-image.sh "prompt" out.png
```

By default, the helper refuses to overwrite an existing output file. To overwrite intentionally:

```bash
LOCALAI_IMAGE_OVERWRITE=1 /Users/nizarayed/.agents/skills/localai-image/generate-image.sh "prompt" out.png
```

## Notes

- No cloud API key is needed.
- The LocalAI response currently returns an image `url`, not `b64_json`; the helper supports both.
- If direct LAN access stops working, verify the service from SSH:

```bash
ssh -o RemoteCommand=none -o RequestTTY=no pc-master.local \
  "powershell -NoProfile -Command \"Invoke-RestMethod -Uri 'http://127.0.0.1:11435/v1/models' | ConvertTo-Json -Depth 5\""
```
