# Email Layout and Signatures

This reference retains its existing filename for compatibility. It contains layout and signature rules only. Expression-style analysis, contact imitation, and tone profiles have been removed.

## Account-specific branding

- `nizar@longhornip.com`: use `../../email-manager/references/LONGHORNIP-EMAIL-TEMPLATE.html` and the Longhorn IP signature below.
- `nizar.ayed@chain-it.com`: use `../../email-manager/references/CHAINIT-EMAIL-TEMPLATE.html` and the Chain-IT signature below.
- Apply these layouts to all emails, including short replies, unless the user explicitly selects another layout.
- Never use `config/signature.json` as a universal signature. Its current values describe Chain-IT, not Longhorn IP.
- A layout-only update must not change the message's wording, language, recipients, or attachments.

## Longhorn IP signature

Use the identity already established in Longhorn IP correspondence. Keep the Longhorn IP template's logo in the header; do not add a second logo.

```html
<p style="margin:0;font-size:12px;color:#545454;line-height:1.5">
  <strong>Nizar S. Ayed</strong><br>
  VP Engineering - Europe<br>
  Longhorn IP LLC<br>
  <a href="https://www.longhornip.com" style="color:#6a593d;text-decoration:none">www.longhornip.com</a><br>
  <a href="https://www.linkedin.com/in/nizarayed/" style="color:#6a593d;text-decoration:none">https://www.linkedin.com/in/nizarayed/</a><br>
  Mobile | +33 6 87 57 46 35
</p>
```

## Chain-IT signature

Populate placeholders from `../config/signature.json` without changing the selected sending account. Use `title.en` or `title.fr` for the message's selected language. HTML-escape all configuration values.

```html
<p style="margin:0;font-family:Futura,Inter,Arial,sans-serif;color:#424242;line-height:1.5">
  <strong>{{NAME}}</strong><br>
  {{TITLE}}<br><br>
  {{MOBILE_LABEL}} {{PHONE}}<br>
  {{EMAIL_LABEL}} <a href="mailto:{{EMAIL}}" style="color:#7A1A2E;text-decoration:none">{{EMAIL}}</a><br>
  Web: <a href="{{WEBSITE}}" style="color:#7A1A2E;text-decoration:none">{{WEBSITE}}</a>
</p>
```

Labels: English uses `Mobile:` and `Email:`; French uses `FR Mobile :` and `eMail:`. These are signature labels, not message-language or wording rules.

Preserve the established confidentiality footer when required:

- English: This message and any attachments are intended solely for their recipients and are confidential. If you received this message in error, please delete it and notify the sender immediately. Any unauthorized use or distribution is prohibited. Because internet communications cannot guarantee message integrity, Chain-IT.com accepts no liability for alteration or modification. Please consider the environment before printing this message.
- French: Ce message et toutes les pièces jointes sont établis à l'intention exclusive de ses destinataires et sont confidentiels. Si vous recevez ce message par erreur, merci de le détruire et d'en avertir immédiatement l'expéditeur. Toute utilisation ou diffusion non autorisée de ce message est interdite. Internet ne permettant pas d'assurer l'intégrité de ce message, Chain-IT.com décline toute responsabilité en cas d'altération ou de modification. Pensez à l'environnement, n'imprimez ce message qu'en cas de nécessité !

Do not claim that the user approved an AI-generated message before the user has approved it.

## Dedicated contextual signatures

For a user-identified miXYtes email, use the dedicated template, signature, and image assembly instructions in `../../email-manager/SKILL.md`. This exception does not change either account's default layout.
