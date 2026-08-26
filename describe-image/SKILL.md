---
name: describe-image
description: Describe images in detail using pi + a vision model. Supports any provider with vision capabilities (OpenAI, Anthropic, Google Gemini, etc.).
---

# Describe Image

Describe images using pi's vision model support. Each image produces a Markdown description file with detailed analysis.

## When to use this skill

First determine whether the current model has vision capabilities. If it does, use the `read` tool directly on the image; do not run this script. Use this script only when the current model cannot inspect images itself, or when the user specifically requests a separate vision-model description.

## Usage

```bash
# Basic — describe one or more images
./describe-image.sh photo.png screenshot.jpg

# Custom provider and model
./describe-image.sh --provider openai-codex --model gpt-5.4-mini diagram.png

# Custom output directory
./describe-image.sh --output-dir ./descriptions image.png
```

Each image generates a `<name>_description.md` file next to it (or in `--output-dir`).

## Requirements

- pi installed and authenticated with a provider that supports vision (default: openai-codex / gpt-5.4-mini)
- The provider/model must accept image inputs
