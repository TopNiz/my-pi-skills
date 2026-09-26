# Agenda Pattern

Use this sub-skill when a slide requires a graphical composition that is not provided by the user's existing PowerPoint placeholders, such as an agenda, timeline, dashboard, pillar model, process diagram, or organization chart.

## Core principle

The user's presentation remains the source of truth for:

- slide master and selected slide layout;
- theme fonts and theme colors;
- background, branding, margins, and overall visual identity;
- editorial content and wording.

A template presentation supplies reusable graphical patterns only. A pattern is a geometry transplant, not a complete slide replacement.

## Terminology

Distinguish these objects carefully:

- **Target presentation**: the user's presentation being enhanced.
- **Target layout**: the existing layout selected for the new or existing target slide.
- **Pattern source slide**: a slide in a template presentation whose foreground shapes demonstrate a reusable composition.
- **Pattern source layout**: the layout or master from which the source slide may inherit a background or other elements.
- **Pattern**: the semantic and geometric recipe extracted from the source slide.

A source slide is not necessarily a reusable PowerPoint layout. Its foreground graphics are often stored directly in `ppt/slides/slideN.xml`, while its background may be stored in `ppt/slideLayouts/slideLayoutN.xml` or a slide master.

## Source-of-truth rules

1. Start from the user's target slide layout. Do not replace it with the template layout.
2. Preserve the target master, theme, background, branding, and inherited text styles.
3. Copy only the requested graphical elements from the pattern source slide.
4. Do not copy template example text, logos, photographs, or decorative branding unless explicitly requested.
5. Keep copied elements editable. Do not use a screenshot as a substitute for editable shapes.
6. Treat the target slide's content as authoritative. Template text is only a structural clue.
7. Remap colors deliberately. A source `accent1` reference resolves according to the target theme after copying; use this behavior only when it is desired.

## Inspection workflow

Before implementing a pattern, inspect both the target presentation and the pattern source:

1. Enumerate target layouts, placeholders, theme fonts, theme colors, slide dimensions, and aspect ratio.
2. Identify the source slide and record its relationship to its source layout and master.
3. Enumerate source shape order, shape names, shape types, groups, connectors, positions, sizes, rotations, fills, lines, text boxes, and relationships.
4. Determine which elements are direct slide shapes and which elements are inherited from the source layout or master.
5. Record the semantic roles of the elements, for example `agenda_bar_1`, `agenda_number_1`, `agenda_heading_1`, and `agenda_body_1`.
6. Store geometry in normalized coordinates or in source-slide units so it can be scaled to the target slide.

## Transplant workflow

1. Reuse an existing target slide when it is the correct layout, or add a slide using the target presentation's existing layout.
2. Preserve the target slide background and master. Do not copy the source layout background by default.
3. Deep-copy the required source slide shape XML into the target slide's shape tree, preserving z-order, groups, transforms, geometry, fills, lines, and effects.
4. For source shapes containing relationships, copy the related media or chart parts and update relationship IDs safely. Pure vector shapes and text do not require media relationships.
5. Replace source text through semantic roles, not by relying only on shape IDs or incidental ordering.
6. Use the target presentation's typography and theme where the target design requires it. Preserve source geometry and visual relationships.
7. Scale or translate the pattern to the target slide dimensions while preserving relative spacing and proportions.
8. Remove or omit source-only items such as sample text, template photos, logos, and source background elements.
9. Render the result and inspect it before reporting completion.

## Python and OOXML guidance

`python-pptx` is appropriate for inspecting presentations and changing text, but it does not provide a complete high-level API for cloning arbitrary shapes between presentations. For faithful transplantation, use controlled OOXML deep copies when necessary:

```python
from copy import deepcopy

source_element = source_shape.element
target_tree = target_slide.shapes._spTree
target_tree.insert_element_before(deepcopy(source_element), "p:extLst")
```

This is only safe for elements whose dependencies are handled. Images, charts, SmartArt, and other relationship-backed objects require relationship and package-part handling. Validate the resulting `.pptx` with `unzip -t` and by reopening it with `python-pptx` or PowerPoint-compatible software.

Do not modify the target slide master, target slide layout, or target theme merely to make the transplanted pattern fit. Adapt the copied pattern instead.

## Example: agenda-bars pattern

Use slide 3 of `ESG Innovation Sustainability PowerPoint Templates.pptx`, from the configured `POWERPOINT_TEMPLATES_DIR`, as the pattern source for this example. Its composition is documented in [the agenda-bars description](../assets/templates/03-agenda-bars.md):

- the source slide contains a title text box;
- four editable colored rectangles form the horizontal bars;
- four editable number text boxes sit over the bars;
- four groups contain a heading and a two-line body text block;
- the source slide uses no foreground placeholders;
- its bulb image is inherited from its source layout background and is excluded by default.

The semantic mapping should be equivalent to:

```text
agenda_title
agenda_bar_1..4
agenda_number_1..4
agenda_heading_1..4
agenda_body_1..4
```

The target slide keeps its own background, master, fonts, and palette. The generator copies the editable bar and text geometry, then inserts the user's agenda content.

## Validation checklist

After transplantation, verify:

- the target slide still uses the target presentation's intended layout;
- the target master, theme, background, and branding are unchanged;
- copied shapes remain editable and have the intended z-order;
- groups, rotations, connectors, and relative positions are preserved;
- source example text, logos, and photographs were not copied accidentally;
- theme colors resolve as intended in the target presentation;
- all target text fits without clipping or unexpected autofit;
- the package reopens successfully;
- the rendered slide matches the intended pattern while remaining stylistically native to the target deck.

Future graphical patterns should be documented with a source slide, semantic roles, copied elements, excluded elements, geometry rules, target-content rules, and a validation checklist.
