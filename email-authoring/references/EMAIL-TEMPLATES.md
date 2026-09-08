# 📧 Email Content Templates

Standard HTML templates for email body content — tables, headings, formatting.
Use these when drafting structured emails (invoices, reports, data comparisons, etc.).

---

## 🎨 Base Stylesheet

Embed this `<style>` block in the `<head>` of every HTML email that uses tables or structured content.

```html
<style>
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    line-height: 1.6;
    color: #333;
  }
  .container {
    max-width: 600px;
    margin: 0 auto;
    padding: 20px;
  }
  h2 {
    color: #2563eb;
    font-size: 16px;
    margin: 20px 0 10px;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    margin: 10px 0 15px;
  }
  th {
    background: #2563eb;
    color: white;
    padding: 8px 12px;
    text-align: left;
    font-weight: 600;
  }
  td {
    padding: 8px 12px;
    border-bottom: 1px solid #e5e7eb;
  }
  tr:nth-child(even) td {
    background: #f9fafb;
  }
  .total {
    font-weight: bold;
    color: #dc2626;
    font-size: 1.1em;
  }
</style>
```

### Color reference

| Token | Hex | Usage |
|-------|-----|-------|
| `--blue` | `#2563eb` | Table headers, section titles |
| `--red` | `#dc2626` | Totals, amounts due |
| `--border` | `#e5e7eb` | Table row borders |
| `--stripe` | `#f9fafb` | Alternating row background |
| `--text` | `#333` | Body text |

---

## 📊 Table Templates

### Simple 2-column data table

Best for: key-value pairs, readings, comparisons.

```html
<h2>Section title</h2>
<table>
  <tr><th style="width:60%">Description</th><th>Valeur</th></tr>
  <tr><td>Label 1</td><td><strong>Value 1</strong></td></tr>
  <tr><td>Label 2</td><td><strong>Value 2</strong></td></tr>
  <tr><td>Label 3</td><td><strong>Value 3</strong></td></tr>
</table>
```

### Multi-section data (repeated tables)

For emails with multiple data groups (e.g., meter readings + invoice details + calculation):

```html
<h2>📊 Section 1</h2>
<table>
  <tr><th style="width:60%">Description</th><th>Valeur</th></tr>
  <tr><td>Item A</td><td><strong>Value</strong></td></tr>
  <tr><td>Item B</td><td><strong>Value</strong></td></tr>
</table>

<h2>💧 Section 2</h2>
<table>
  <tr><th style="width:60%">Description</th><th>Valeur</th></tr>
  <tr><td>Item C</td><td>Value</td></tr>
  <tr><td>Montant total</td><td>1 234,56 €</td></tr>
</table>

<h2>🧮 Section 3</h2>
<table>
  <tr><th style="width:60%">Calcul</th><th>Montant</th></tr>
  <tr><td>83 m3 × 4,5227 €</td><td class="total">= 375,38 €</td></tr>
</table>
```

---

## 📝 Full Email Layout

Use this structure for complete HTML emails with content tables + signature.

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; }
  .container { max-width: 600px; margin: 0 auto; padding: 20px; }
  h2 { color: #2563eb; font-size: 16px; margin: 20px 0 10px; }
  table { border-collapse: collapse; width: 100%; margin: 10px 0 15px; }
  th { background: #2563eb; color: white; padding: 8px 12px; text-align: left; font-weight: 600; }
  td { padding: 8px 12px; border-bottom: 1px solid #e5e7eb; }
  tr:nth-child(even) td { background: #f9fafb; }
  .total { font-weight: bold; color: #dc2626; font-size: 1.1em; }
</style>
</head>
<body>
<div class="container">

  <!-- Greeting -->
  <p>Bonjour [Name],</p>

  <!-- Intro paragraph -->
  <p>...</p>

  <!-- Data tables -->
  <h2>Section 1</h2>
  <table>
    <tr><th style="width:60%">Description</th><th>Valeur</th></tr>
    <tr><td>Item</td><td><strong>Value</strong></td></tr>
  </table>

  <!-- More sections... -->

  <!-- Sign-off -->
  <p>Bonne journée,</p>

  <!-- SIGNATURE — Paste from STYLE-GUIDE.md section 11 -->
  {{SIGNATURE}}

</div>
</body>
</html>
```

---

## ⚡ Quick Reference for the Agent

When drafting a structured email:

1. **Start with the base stylesheet** (`<style>` block above)
2. **Wrap body in `<div class="container">`**
3. **Use `<h2>` for section titles**
4. **Use `<table>` with `<th>` for data**
5. **Use `.total` class for financial highlights**
6. **Append signature** from `STYLE-GUIDE.md` section 11 (French or English, HTML or plain text)
7. **Always send multipart/alternative** (HTML + plain text fallback)
