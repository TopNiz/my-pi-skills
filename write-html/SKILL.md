---
name: write-html
description: Write clean, accessible, semantic HTML documents. Prioritises semantic HTML5 tags over generic <div> elements. Uses <div> only for pure presentational wrappers that have no semantic meaning (e.g., scroll containers, layout grids). For all content-bearing elements, use the correct semantic tag.
allowed-tools: read write edit bash
---

# 📝 Write Semantic HTML

Write HTML that is **clean, accessible, and semantically correct**. The guiding principle: **every content-bearing element should use the most specific semantic HTML5 tag available.** Use `<div>` only when no semantic tag fits and the purpose is purely presentational.

---

## 🧭 Semantic Tag Reference

### Document structure

| Tag | When to use | Examples in articles |
|-----|-------------|---------------------|
| `<main>` | Wraps the primary content of the page. One per page. | `article-container`, the main reading area |
| `<header>` | Introductory content: hero image, title, meta info, navigation. | Article hero + title block |
| `<footer>` | Closing content: sources, copyright, related links. | Source citations section |
| `<section>` | A thematic grouping of content, typically with a heading. Each `<section>` should have an `aria-labelledby` pointing to its heading's `id`. | Each chapter/topic in an article |
| `<article>` | A self-contained composition (blog post, news story, comment). | The whole article (use when the page has multiple independent pieces) |

### Text & semantics

| Tag | When to use | Instead of |
|-----|-------------|------------|
| `<p>` | Paragraphs of text. | `div.subhead`, `div.meta` (if it's text content) |
| `<time datetime="...">` | Dates and times. Machine-readable date in `datetime` attribute. | Plain `span.date` |
| `<strong>` | Strong importance (bold). | `<span style="font-weight:bold">` |
| `<em>` | Stressed emphasis (italic). | `<span style="font-style:italic">` |
| `<blockquote>` | A block quotation. | `div.pull-quote` wrapping text |
| `<cite>` | Title of a work (book, paper, article). | Plain styling |

### Lists

| Tag | When to use | Instead of |
|-----|-------------|------------|
| `<ul>` / `<ol>` / `<li>` | Any list of items — not just bullet lists. Data grids, stat cards, feature lists. | `div.data-grid` with `div.item` children |
| `<dl>` / `<dt>` / `<dd>` | Name-value groups (definitions, metadata pairs). | `div` pairs for key-value data |

Example — stat cards as a list:
```html
<ul class="data-grid">
  <li>
    <span class="num">1.20%</span>
    <span class="desc">German, the next closest language</span>
  </li>
</ul>
```

### Media

| Tag | When to use | Instead of |
|-----|-------------|------------|
| `<figure>` | Any image, chart, diagram, or illustration. Wraps the media + its caption. | `div.image-block` |
| `<figcaption>` | Caption for the figure's content. Must be a child of `<figure>`. | `div.caption` |
| `<img>` | Images. Always include a meaningful `alt` attribute. | — |

```html
<figure>
  <img src="chart.png" alt="English dominance comparison across GPT-3, Llama 2, and PaLM">
  <figcaption>English as a percentage of training data. The web average (41%) is shown as a reference line.</figcaption>
</figure>
```

### Tables

| Tag | When to use | Instead of |
|-----|-------------|------------|
| `<table>` | Tabular data (rows and columns). | CSS grid or flexbox pretending to be a table |
| `<caption>` | Title/description of the table (use `.sr-only` if visually hidden). | Heading before the table |
| `<thead>` / `<tbody>` / `<tfoot>` | Structural table sections. | — |
| `<th scope="col">` / `scope="row"` | Column or row headers. Required for accessibility. | `<td>` with bold styling |
| `<tr>` / `<td>` | Rows and data cells. | — |

### Highlights & callouts

| Tag | When to use | Instead of |
|-----|-------------|------------|
| `<aside>` | Content tangentially related to the main flow: callout boxes, pull quotes, side notes, stats highlights. | `div.callout`, `div.pull-quote`, `div.data-highlight` |

```html
<aside class="callout">
  <em>93%</em> of GPT-3's training documents were in English.
</aside>

<aside class="pull-quote">
  <blockquote>"This is not a technical limitation. It's a decision about what we value."</blockquote>
</aside>
```

### Inline references

For inline citations, use anchor links to footnotes — not bare superscript numbers:

```html
German, at just <em>1.2%</em>.<a href="#source-1" class="cite">[1]</a>
```

And at the bottom:
```html
<footer class="sources">
  <h3>Sources</h3>
  <ol>
    <li id="source-1">...</li>
  </ol>
</footer>
```

---

## ✅ When It's OK to Use `<div>`

`<div>` is acceptable when **no semantic HTML5 element fits** and the element is **purely presentational**:

| Case | Example |
|------|---------|
| Scroll wrapper for overflow | `<div class="table-wrap">` (needed for horizontal scroll on small screens, no semantic equivalent) |
| Layout-only container | A div that exists only to apply `display: flex` or `display: grid` for visual arrangement |
| Generic wrapper for styling | A wrapper that groups elements purely for margin/padding/spacing |

```html
<!-- ✅ OK: purely presentational scroll wrapper -->
<div class="table-wrap">
  <table>...</table>
</div>

<!-- ❌ Not OK: a div acting as a callout -->
<div class="callout">...</div>
<!-- ✅ Use: -->
<aside class="callout">...</aside>
```

---

## 🔍 Quick Decision Guide

Ask: **"Does this content have semantic meaning?"**

```
Is the element content-bearing?
  ├── Yes → Is there a semantic HTML5 tag for it?
  │         ├── Yes → Use that tag (<section>, <figure>, <aside>, <nav>, etc.)
  │         └── No  → Use <div> (only for presentational/layout purposes)
  └── No  → Use <div> (purely presentational wrapper)
```

---

## 🧪 Validation Checklist

Before considering HTML done:

- [ ] Is every image wrapped in `<figure>` with a `<figcaption>`?
- [ ] Are all callouts, pull quotes, stat boxes using `<aside>`?
- [ ] Is the article scope wrapped in `<main>`?
- [ ] Is there a `<header>` for the intro block (hero + meta + title)?
- [ ] Are sources in a `<footer>`?
- [ ] Do all `<section>` elements have `aria-labelledby="s-..."` matching their `<h2 id="s-...">`?
- [ ] Does the date use `<time datetime="...">`?
- [ ] Are data grids using `<ul>` / `<li>` instead of nested `<div>`s?
- [ ] Does the table have `<th scope="col">` and a `<caption>` (visible or `.sr-only`)?
- [ ] Is `<div>` used only for presentational wrappers (scroll, layout) — never for content?
