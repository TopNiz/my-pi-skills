# Build a new deck from a template

Use `scripts/build_from_template.py` when creating a new presentation from a reference `.pptx` that contains the desired masters, layouts, theme and placeholder styles. The helper runs on any machine with Python and `python-pptx`; it does not call Keynote, PowerPoint, AppleScript or other desktop applications.

Reference decks are not part of this skill: they live in the directory configured by `POWERPOINT_TEMPLATES_DIR` in the skill-local `.env` (see `.env.example`). `--template` accepts either an explicit path or a bare filename that is resolved inside that directory.

First inspect the available layouts:

```bash
python scripts/build_from_template.py \
  --template "Modern Business Proposal by Slidesgo.pptx" \
  --spec /path/to/empty-spec.json \
  --output /tmp/inspect-only.pptx \
  --list-layouts
```

If the deck is missing, the helper reports which variable to check rather than failing cryptically. A missing template deck is a normal condition on a machine that has not configured a library.

Use `--clear-slides` only for a new derived deck. It removes the sample slides from the in-memory copy while preserving the template's masters, layouts, theme, and media. Do not use it when editing an existing user deck.

The specification is JSON. `layout` is the exact existing layout name. `title` targets the title placeholder. `text` and `lists` target placeholders by their existing `idx`; `lists` creates separate paragraphs and inherits the placeholder's bullet and paragraph treatment. `images` inserts an image through the selected picture placeholder.

```json
{
  "slides": [
    {
      "layout": "TITLE",
      "title": "Chain-IT",
      "text": {"1": "From algorithmic thinking to enterprise AI"},
      "images": {"2": "/path/to/logo.png"}
    },
    {
      "layout": "CUSTOM_6",
      "title": "The Chain-IT approach",
      "text": {"4": "Identify", "5": "Build", "6": "Govern"},
      "lists": {
        "1": ["Diagnose with teams", "Map opportunities"],
        "2": ["Co-design in short cycles", "Transfer skills"],
        "3": ["Set governance roles", "Track KPIs"]
      }
    }
  ]
}
```

The helper validates the reopened presentation, slide-to-layout associations and ZIP package before returning success. Keep the JSON specification and the generated deck together when a build must be reproducible.
