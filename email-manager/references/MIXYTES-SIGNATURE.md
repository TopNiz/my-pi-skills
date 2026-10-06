# miXYtés email signature

Use this signature for emails sent by Nizar Ayed in his capacity as Vice-President of miXYtés.

The HTML structure and styling follow the signature used by Hélène Courson in a miXYtés email. The email address line is intentionally omitted for now.

The logo is embedded inline in the MIME message with the content ID `miXYtes-logo` and sourced from:

`references/miXYtes-logo.png`

## HTML signature fragment

```html
<table id="table_0" cellspacing="0" cellpadding="0" border="0" style="box-sizing: border-box; border-collapse: collapse; border-spacing: 0px;"><tbody><tr><td style="border-width: 1pt; border-style: solid; border-color: white; padding: 0cm 5.4pt; width: 113pt;"><span style="font-family: Aptos, Arial, Helvetica, sans-serif; font-size: 12pt; color: rgb(0, 0, 0); line-height: 2rem;"><img src="cid:miXYtes-logo" alt="Résultat de recherche d'images pour &quot;mixytes metz&quot;" id="Image_x0020_1" width="108" height="90" style="width: 1.125in; height: 0.9479in; max-width: 100%;"></span></td><td style="border-width: 1pt 1pt 1pt medium; border-style: solid solid solid none; border-color: white white white currentcolor; padding: 0cm 5.4pt; width: 184.3pt;"><div style="font-family: Aptos, Arial, Helvetica, sans-serif; font-size: 12pt; color: rgb(237, 125, 49);"><span style="line-height: 2rem;">Nizar AYED</span></div><div style="font-family: Aptos, Arial, Helvetica, sans-serif; font-size: 12pt; color: rgb(237, 125, 49);"><span style="line-height: 2rem;">Vice-Président</span></div><div style="font-family: Aptos, Arial, Helvetica, sans-serif; color: black; font-size: 12pt;"><span style="line-height: 2rem;">06 87 57 46 35</span></div></td></tr></tbody></table>
```

## Plain-text fallback

```text
Nizar AYED
Vice-Président
06 87 57 46 35
```

## MIME requirements

- Use `multipart/alternative` for the plain-text and HTML versions.
- Make the HTML branch `multipart/related`.
- Attach `references/miXYtes-logo.png` to the related part as an inline `image/png`.
- Set the image `Content-ID` header to `<miXYtes-logo>`.
- Do not add an email address until one is explicitly provided.
