---
name: powerpoint
description: Create and edit PowerPoint presentations while preserving the presentation's existing slide layouts, placeholder styles, bullets, theme fonts, colors, and geometry. Use when filling a user-provided .pptx based on its built-in layouts.
compatibility: Requires Python 3 with python-pptx for editing. Cross-platform visual QA can use LibreOffice/soffice and Poppler; desktop automation is optional.
---

# PowerPoint Layout-Preserving Skill

Use this skill when a presentation must be filled **using its existing design**, rather than restyled by the agent.

The presentation's slide layouts are the source of truth. Treat their placeholders, inherited text styles, bullets, colors, spacing, and geometry as part of the user's design system.

## Environment

```bash
uv sync        # builds .venv from pyproject.toml (python-pptx)
```

Run the helper scripts with that interpreter (`uv run python scripts/build_from_template.py ...`), or with any Python 3 that has `python-pptx` installed.

## Non-negotiable rules

1. **Inspect before editing.** Enumerate the presentation's layouts, names, placeholder indices, placeholder types, and positions before adding content.
2. **Use an existing layout.** Add slides with `prs.slides.add_slide(existing_layout)`; never recreate a layout with a blank slide and manually positioned substitutes.
3. **Use placeholders first.** Put titles, body text, captions, images, and columns into the placeholders supplied by the selected layout.
4. **Inherit styles.** Set text content only. Do not set font size, font family, bold, color, alignment, margins, autofit, or bullet characters unless the user explicitly requests a style change.
5. **Preserve bullets and levels.** Create separate paragraphs for list items and use the placeholder's existing paragraph levels. Do not manually add bullet characters such as `•` or `-`.
6. **Do not add unnecessary shapes.** A free-form text box is acceptable only when the chosen layout has no suitable placeholder, notably `Blank` or `Title Only`.
7. **Validate visually.** Export at least the slide being worked on to an image in a temporary directory and inspect it before reporting completion.

## Reference templates (local, configured — never shipped)

The decks used as geometry and typography references are **not part of this
skill** and are never committed, shipped or advertised. They are third-party
branded templates whose redistribution is not permitted. They live outside the
repository, in a directory each machine configures in the skill-local `.env`:

```bash
cp .env.example .env      # then set POWERPOINT_TEMPLATES_DIR
```

```ini
POWERPOINT_TEMPLATES_DIR=~/MyDocuments/Templates
```

`.env` is gitignored; `.env.example` documents the variable. `--templates-dir`
and the `POWERPOINT_TEMPLATES_DIR` environment variable override it for a single
run.

These decks are **reference inputs, not deliverables**. Consult them to read off
layout composition, geometry, palette and typography, then apply what you learn
to the user's own deck. Never hand a template deck to the user as output, and
never import its text, logo or photography (see the provenance rule below).

What *is* committed, and remains useful even where the decks are absent, is this
skill's own analysis: the per-slide pattern descriptions in
[assets/templates/](assets/templates/) and the matching catalog.

Decks this library draws on, when present in the configured directory:

- `ESG Innovation Sustainability PowerPoint Templates.pptx`: 48-slide ESG pattern source, with a Keynote version alongside it.
- `industry 4.0-Revolution-PowerPoint-Templates.pptx`: Industry patterns, including the annotated agenda on slide 3.
- `Modern Business Proposal by Slidesgo.pptx`: compact table of contents on slide 3; declared fonts and palette on slide 12.
- `TPL_Natural-Green-Background-PowerPoint-Templates.pptx`: natural green template.
- `TPL_Transparent Skeletal Leaves PowerPoint Templates.pptx`: skeletal leaves template.

Always check that a deck is actually present before relying on it; treat a
missing deck as a normal condition, not an error.

For ESG pattern selection, read [the matching catalog](assets/templates/template-matching-catalog.yaml), then only the relevant `source_doc`. `source_doc` is resolved relative to the catalog's own directory; `template_file` is resolved inside `POWERPOINT_TEMPLATES_DIR`. The catalog currently covers the ESG deck only. Other decks require inspection of the relevant slides.

The target presentation supplies content and styling. Reference patterns can supply composition without importing the source's visual identity.

## Build new decks from a reference template

When there is no existing target deck and the user wants a new deck based on a reference `.pptx`, use [scripts/build_from_template.py](scripts/build_from_template.py) instead of writing a one-off builder or automating Keynote/PowerPoint. Read [the builder reference](references/build-from-template.md) for the JSON specification.

The builder keeps the reference deck's masters, layouts, theme and placeholder styles, and populates slides through those existing placeholders. Pass `--clear-slides` only when creating a new derived deck from a template that contains sample slides. It validates the reopened presentation and the ZIP package before returning success. Pass `--template` either an explicit path or a bare filename resolved inside `POWERPOINT_TEMPLATES_DIR`, so the same invocation works on any machine that has the template library configured.

For an existing user deck, do not clear or rebuild the deck: inspect it and edit it in place with `python-pptx` using the workflow below.

## Specialized sub-skill references

- [Agenda Pattern](references/001-agenda-pattern.md): copy editable graphical compositions from pattern source slides into the user's existing presentation while preserving the user's master, layout, theme, background, and visual identity.
- [Project-native three-slide batches](references/project-native-three-slide-batches.md): extend an approved deck three slides at a time, preserve all prior package entries, validate XML and relationships before rendering, visually inspect only the new pages, and promote the candidate after QA.

This graphical-pattern workflow extends the placeholder-first workflow for slides whose composition is made from direct shapes, groups, connectors, or other editable graphics rather than standard placeholders.

## 1. Inspect the presentation

```python
from pptx import Presentation

prs = Presentation(input_path)
print("slides:", len(prs.slides))
print("layouts:", len(prs.slide_layouts))

for index, layout in enumerate(prs.slide_layouts):
    print(index, layout.name)
    for placeholder in layout.placeholders:
        fmt = placeholder.placeholder_format
        print("  idx=", fmt.idx, "type=", fmt.type, "name=", placeholder.name,
              "box=", (placeholder.left, placeholder.top,
                        placeholder.width, placeholder.height))
```

Important observations:

- `slide_layouts` contains the layouts defined by the deck; use those objects directly.
- `slide.shapes.title` returns the title placeholder when one exists. Some layouts have a vertical title; it is still the title placeholder.
- A `Blank` layout has no title or body placeholder. Do not pretend it has one.
- Placeholder `idx` values are useful for distinguishing several body or picture placeholders in layouts such as `Comparison`, `3 Column`, and `3 Picture Column`.
- Placeholder types include title, body, object/content, picture, date, footer, and slide number. Date/footer/number placeholders are normally not content targets.

## 2. Decide whether to reuse an existing slide

An empty starter deck may already contain one empty slide, often using the first layout. Reuse that slide when it is already the correct layout, then add slides only for the remaining layouts. This produces one representative slide per available layout without leaving an unused blank slide.

Never remove an existing slide unless the user explicitly asks for that operation.

## 3. Populate text without overriding the layout

Use helpers that change only text and paragraph structure:

```python
def placeholder_by_idx(slide, idx):
    for shape in slide.placeholders:
        if shape.placeholder_format.idx == idx:
            return shape
    return None


def put_text(shape, text):
    """Replace content while leaving inherited formatting untouched."""
    if shape is None or not shape.has_text_frame:
        return
    frame = shape.text_frame
    frame.clear()
    for line_number, line in enumerate(text.split("\\n")):
        paragraph = frame.paragraphs[0] if line_number == 0 else frame.add_paragraph()
        paragraph.text = line
        # Do not set paragraph.font, run.font, bullet properties, or size.


def put_list(shape, items):
    """Create list paragraphs and inherit bullets/styles from the placeholder."""
    if shape is None or not shape.has_text_frame:
        return
    frame = shape.text_frame
    frame.clear()
    for item_number, item in enumerate(items):
        paragraph = frame.paragraphs[0] if item_number == 0 else frame.add_paragraph()
        paragraph.text = item
        # Keep the level supplied by the layout. Set paragraph.level only when
        # a deliberate non-default hierarchy is required.
```

Title example:

```python
slide = prs.slides.add_slide(prs.slide_layouts[1])
put_text(slide.shapes.title, "Title and Content")
put_list(placeholder_by_idx(slide, 1), [
    "Contexte local",
    "Opportunités de l'IA",
    "Prochaine étape : cadrer un cas d’usage",
])
```

Do **not** do this for normal layout placeholders:

```python
run.font.size = Pt(28)
run.font.bold = True
run.font.name = "Arial"
run.font.color.rgb = RGBColor(...)
paragraph.font.size = Pt(18)
shape.text = "• Item 1\\n• Item 2"
```

Those operations create direct formatting and can override the layout/master defaults. Use plain text and separate paragraphs instead.

## 4. Match content to the layout

Use the layout's placeholder arrangement to choose sample or real content:

| Layout pattern | Appropriate content |
|---|---|
| Title slide | Title plus subtitle or short introduction |
| Title and content | One list or structured body content |
| Section header | Short section title and transition sentence |
| Two content | Two parallel lists or two related blocks |
| Comparison | Headings in the two header placeholders and content in the two body placeholders |
| Title only | Title plus a minimal additional object only if sample content is required |
| Blank | Minimal free-form sample content; no title placeholder exists |
| Content with caption | Main object/content placeholder plus caption |
| Picture with caption | Picture placeholder plus caption |
| Panoramic picture with caption | Wide picture placeholder plus caption |
| Title and caption | Title plus a short caption/message |
| Quote with caption | Quote placeholder plus attribution/caption |
| Name card | Short identity, role, and objective block |
| 3 Column | Use each column's heading and body placeholders |
| 3 Picture Column | Insert an image into each picture placeholder and use the associated heading/caption placeholders |
| Vertical title/text | Keep text concise; the layout controls rotation and placement |

For a picture placeholder, use the placeholder's own insertion method:

```python
picture_placeholder = placeholder_by_idx(slide, picture_idx)
picture_placeholder.insert_picture(temp_image_path)
```

Do not add a separate image on top of a picture placeholder unless there is a specific reason; that defeats the layout's cropping and geometry.

## 5. Handle layouts with no content placeholder

`Blank` and `Title Only` may require a text box for a demonstration. Keep it unformatted so it uses the theme's generic defaults as far as possible:

```python
from pptx.util import Inches

box = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(10), Inches(2))
put_text(box, "Sample content for a layout without a content placeholder.")
```

This is an exception, not a replacement for using placeholders. Do not manually imitate a title or body placeholder on these slides.

## 6. Repair accidental direct formatting

If a first implementation used explicit font sizes, bold, colors, or paragraph default sizes, remove those direct-formatting nodes from the **populated slide XML** while leaving layout, master, and theme XML untouched. Direct formatting is represented by elements such as `a:rPr` and `a:defRPr` in `ppt/slides/slide*.xml`.

A controlled cleanup can be performed by rewriting the package to a temporary `.pptx` and replacing only the explicitly authorized target file:

```python
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree
import os, tempfile

ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
fd, temporary_path = tempfile.mkstemp(suffix=".pptx", dir=os.path.dirname(target_path))
os.close(fd)
try:
    with ZipFile(target_path, "r") as source, ZipFile(temporary_path, "w", ZIP_DEFLATED) as output:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename.startswith("ppt/slides/slide") and item.filename.endswith(".xml"):
                root = etree.fromstring(data)
                for node in root.xpath(".//a:rPr | .//a:defRPr", namespaces=ns):
                    node.getparent().remove(node)
                data = etree.tostring(data and root, xml_declaration=True,
                                      encoding="UTF-8", standalone=True)
            output.writestr(item, data)
    os.replace(temporary_path, target_path)
finally:
    if os.path.exists(temporary_path):
        os.unlink(temporary_path)
```

Use this only when the direct formatting is known to be unwanted. Do not remove formatting from `slideLayouts`, `slideMasters`, or the theme: those files contain the defaults that must be preserved.

## 7. Save and structurally validate

Save only to a user-authorized destination:

```python
prs.save(target_path)
```

Then reopen the file and verify:

```python
from pptx import Presentation

check = Presentation(target_path)
assert len(check.slides) >= len(check.slide_layouts)
for slide in check.slides:
    assert slide.slide_layout is not None
print("PowerPoint reopened successfully")
```

Also validate the ZIP package:

```bash
unzip -t "<presentation>.pptx"
```

If creating one representative slide per layout, verify the ordered layout names:

```python
print([slide.slide_layout.name for slide in check.slides])
```

## 8. Export and inspect a slide as an image

Always render the slide being worked on into a temporary directory, never into the project folder. Prefer a headless, cross-platform office converter when available:

```bash
TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/powerpoint-layout-check.XXXXXX")
PDF="$TMP_DIR/rendered-slides.pdf"

soffice --headless --convert-to pdf --outdir "$TMP_DIR" "<presentation>.pptx"
pdftoppm -f N -l N -png -r 144 "$PDF" "$TMP_DIR/slide"
```

If `soffice` is unavailable, use another installed headless Office-compatible converter. On macOS, Keynote or Microsoft PowerPoint automation may be used only as a last-resort fallback when the user has authorized desktop automation; never make it the default build path and do not wait indefinitely on an AppleScript export.

`pdftoppm` may produce a zero-padded filename such as `slide-02.png`. Read that image with the image-reading tool and check:

- the intended layout is visible;
- title and body content are inside their placeholders;
- bullets use the deck's own bullet glyph, indentation, and color;
- no text is clipped, unexpectedly resized, or restyled;
- images are cropped by the picture placeholder as intended;
- vertical layouts remain readable;
- no accidental extra shapes or blank slide were introduced.

If the rendering looks wrong, inspect the slide XML for direct `a:rPr` or `a:defRPr` nodes before changing the layout itself.

## Common failure modes

### Content looks too large, too small, or has the wrong weight

Direct formatting was applied. Remove explicit font and paragraph formatting and let the layout/master inherit it.

### Bullets disappeared

The content was entered as literal bullet characters, or the body content was placed in a free-form text box. Use separate paragraphs inside the layout's body/content placeholder.

### A title is missing

The selected layout may have no title placeholder (`Blank`), or the title placeholder may have a nonstandard index/type. Inspect `layout.placeholders` and use `slide.shapes.title` or the correct placeholder index.

### A picture is misplaced or distorted

The image was added as a free-floating shape. Insert it through the layout's picture placeholder.

### A layout is visually altered

Do not edit slide-master/layout/theme XML to accommodate sample content. Shorten the sample text, use the existing placeholder, or choose a more suitable existing layout.
