# Project-native three-slide batch workflow

Use this recipe when extending an established presentation in reviewable batches while preserving every approved slide and the deck's visual language.

## 1. Read only the current batch

For a deck with `N` approved slides:

1. Read only descriptions `N+1` through `N+3`.
2. Inspect the target deck's slide count, dimensions, layouts, and the last approved slides.
3. Read the most recent batch builder to reuse its tested helpers and validation pattern.
4. Do not read later slide descriptions unless the current batch depends on them.

## 2. Reuse native components

Use `python-pptx` and `lxml`.

1. Add each slide with an existing layout, normally the deck's `Title Only` layout for editorial compositions.
2. Clone text treatments, panels, rules, footer elements, and accent lines from approved slides.
3. Change text and geometry only. Keep theme fonts, fills, line styles, and effects inherited from cloned native components.
4. Keep all elements editable. Do not flatten a slide into an image.
5. Add source and qualification details to speaker notes.
6. Check every shape stays within slide bounds and that no text is clipped.

If the active Python lacks `python-pptx`, locate a compatible cached environment rather than repeatedly investigating the toolchain. For example:

```bash
PPTX_DIR=$(find "$HOME/.cache/uv/archive-v0" -path '*/lib/python*/site-packages/pptx' -type d | head -1)
PYTHONPATH="$(dirname "$PPTX_DIR")" python path/to/build_batch.py
```

## 3. Build a candidate without touching the target

1. Read the target bytes before editing.
2. Save a backup copy in a session-owned temporary review directory.
3. Build the extended presentation in memory.
4. Write a candidate PPTX into that temporary directory.
5. Assert that the target bytes are unchanged.

When approval of prior slides must be preserved exactly, copy all pre-existing entries below these package paths byte for byte from the original into the candidate:

- `ppt/slides/`
- `ppt/notesSlides/`
- `ppt/slideMasters/`
- `ppt/slideLayouts/`
- `ppt/notesMasters/`
- `ppt/theme/`
- `ppt/media/`

Update package metadata such as slide and note counts to match the new total.

## 4. Validate before rendering

Only a structurally validated candidate should proceed to rendering.

Validation order:

1. Reopen the candidate with `Presentation(candidate)`.
2. Verify the expected slide count and titles.
3. Run ZIP integrity checking with `ZipFile.testzip()` or `unzip -t`.
4. Parse every `.xml` and `.rels` entry with `lxml.etree.fromstring()`.
5. Resolve every internal relationship target and assert that its package entry exists.
6. Compare protected entries byte for byte with the original.
7. Confirm slide layouts, backgrounds, page numbers, geometry, and text constraints.
8. Record the results in `validation.json` in the temporary review directory.

Do not render or open the candidate in a desktop presentation application before these checks pass.

## 5. Render and inspect only the current batch

Render the validated candidate to a session-owned temporary directory with a headless Office-compatible converter:

```bash
soffice --headless --convert-to pdf --outdir "$REVIEW" "$PPT"
```

Render only the new pages:

```bash
pdftoppm -f "$FIRST" -l "$LAST" -png -r 144 "$PDF" "$REVIEW/slide"
```

Inspect each image for clipping, overlap, weak hierarchy, broken arrows, incorrect numbering, and inconsistent spacing. If a problem is found, adjust the builder, regenerate a fresh candidate, repeat structural validation, and then export again.

## 6. Promote only after QA

After the candidate passes structural and visual review:

1. Replace only the user-authorized target presentation with the candidate.
2. Reopen the final target and confirm the total slide count and new titles.
3. Run ZIP and XML parsing checks once more on the final target.
4. Keep review artifacts in the session-owned temporary directory unless the user requests a deliverable PDF.
5. Stop after the current three-slide batch and request approval before reading or building the next descriptions.
