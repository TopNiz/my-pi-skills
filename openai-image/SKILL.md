---
name: openai-image
description: Generate images using OpenAI's gpt-image models (gpt-image-1, gpt-image-1.5, gpt-image-2). Use for creating infographics, illustrations, diagrams, marketing visuals, and any image generation task.
---

# OpenAI Image Generation

Generate high-quality images using OpenAI's image generation API. Uses your pi-configured OpenAI API key automatically.

## Models Available

| Model | Notes |
|-------|-------|
| `gpt-image-1` | Fast, reliable (default) |
| `gpt-image-1.5` | Improved quality over v1 |
| `gpt-image-2` | Latest model, slower but best quality |

## Sizes

- `1024x1024` (square)
- `1024x1536` (portrait)
- `1536x1024` (landscape/widescreen)

## Quality

- `low` — fastest, lowest cost
- `medium` — balanced
- `high` — best quality (default)
- `auto` — automatic

## Usage

```bash
# Generate an image (all params optional except prompt)
./generate-image.sh "A professional infographic of..." [output.png] [model] [size] [quality]

# Basic — uses defaults (gpt-image-1, 1536x1024, high)
./generate-image.sh "A blue sky with clouds" sky.png

# With specific model
./generate-image.sh "An infographic about AI" ai-infographic.png gpt-image-2

# Square format, medium quality
./generate-image.sh "A logo concept" logo.png gpt-image-1 1024x1024 medium

# Portrait orientation
./generate-image.sh "A vertical banner" banner.png gpt-image-1.5 1024x1536 high
```

## Examples for This Project

### Training program overview
```bash
./generate-image.sh "Professional infographic of AI for Business executive training program from École Polytechnique. 3 connected modules in horizontal flow: Module 1 Strategy & Data (12h in-person), Module 2 Generative AI & Performance (16h remote), Module 3 Governance Ethics & Security (16h remote). Dark navy blue background with bright orange accents. RNCP certification badge. Clean corporate infographic style with modern icons. French text titles." training-program-overview.png gpt-image-2
```

### Module-specific illustration
```bash
./generate-image.sh "Illustration for Module 1 of AI for Business training: Strategy & Data. Data flows and AI brain concept. Dark navy blue and orange colors. Corporate style." module1-strategy.png gpt-image-1
```
