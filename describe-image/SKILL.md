---
name: describe-image
description: Describe images in detail using pi + a vision model. Supports any provider with vision capabilities (OpenAI, Anthropic, Google Gemini, etc.).
---

# Describe Image

Describe images using pi's vision model support. Each image produces a Markdown description file with detailed analysis.

## Usage

```bash
# Basic — describe one or more images
./describe-image.sh photo.png screenshot.jpg

# Custom provider and model
./describe-image.sh --provider openai-codex --model gpt-5.4 diagram.png

# Custom output directory
./describe-image.sh --output-dir ./descriptions image.png
```

Each image generates a `<name>_description.md` file next to it (or in `--output-dir`).

## Requirements

- pi installed and authenticated with a provider that supports vision
- The provider/model must accept image inputs
