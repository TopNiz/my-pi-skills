# Email Category Taxonomy

This document defines the email categorization scheme used by the email-manager skill.
**Edit this file to customize categories for your workflow.**

## Core Categories

When processing emails, assign one **primary category** and optionally **tags**:

### 📄 Invoices & Finance
| Category | Description | Examples | Tags |
|----------|-------------|----------|------|
| `invoice` | Bills, invoices, payment requests | Vendor invoices, SaaS receipts | `urgent`, `pending-payment`, `paid` |
| `payment` | Payment confirmations, receipts | Bank transfer confirmations, PayPal receipts | `received`, `sent` |
| `financial` | Banking, accounting, tax docs | Bank statements, tax notices, expense reports | `tax`, `accounting`, `report` |
| `subscription` | Recurring payments | SaaS renewals, memberships, domain renewals | `annual`, `monthly`, `cancel-by` |

### 💼 Business & Clients
| Category | Description | Examples | Tags |
|----------|-------------|----------|------|
| `client` | Client communications | Project updates, proposals, feedback | `active-project`, `new-lead`, `follow-up` |
| `partnership` | Partner/vendor communications | Supplier quotes, contract renewals, SLA notices | `review`, `signed`, `negotiating` |
| `support` | Support tickets, help desk | Customer issues, tech support | `resolved`, `escalated`, `waiting` |
| `legal` | Legal documents, compliance | Contracts, NDAs, terms updates, GDPR notices | `sign-required`, `review`, `archived` |

### 🛠️ Operations & Tech
| Category | Description | Examples | Tags |
|----------|-------------|----------|------|
| `devops` | Infrastructure, deployments | Server alerts, CI/CD notifications, DNS changes | `alert`, `maintenance`, `deployed` |
| `security` | Security alerts, auth notices | Login from new device, password reset, 2FA changes | `critical`, `suspicious`, `info` |
| `system` | System notifications | Delivery status, bounce backs, storage limits | `error`, `warning`, `info` |

### 👤 Personal & General
| Category | Description | Examples | Tags |
|----------|-------------|----------|------|
| `meeting` | Calendar invites, meeting notes | Google Calendar invites, Zoom links, agendas | `today`, `this-week`, `tentative` |
| `social` | Social media, newsletters | LinkedIn, Twitter/X notifications, mailing lists | `read-later`, `unsubscribe` |
| `personal` | Personal correspondence | Friends, family, personal projects | `reply-needed`, `read` |
| `promotion` | Marketing, offers | Sales, discounts, product announcements | `junk`, `interesting` |

### 🏷️ Special Flags
| Flag | Meaning | Auto-detected when |
|------|---------|-------------------|
| `🔴 urgent` | Requires action today | Keywords: urgent, ASAP, deadline today, overdue |
| `🟡 follow-up` | Needs response within 48h | Keywords: awaiting, response needed, follow-up |
| `🔵 informational` | Read only, no action needed | Newsletters, notifications, status reports |
| `⚪ archive` | Can be filed away | Confirmations, receipts (after processing), auto-replies |

## Invoice-Specific Classification

When `extract-invoices` runs, emails are further classified:

| Sub-category | Criteria | Action |
|-------------|----------|--------|
| `invoice-new` | First occurrence from this sender with invoice PDF | Save + flag for review |
| `invoice-reminder` | Subject contains "reminder" or similar | Flag as pending-payment |
| `invoice-paid` | Payment confirmation or "thank you" email | Mark as paid in index |
| `invoice-overdue` | Subject/body contains "overdue", "late payment" | 🔴 URGENT - escalate |

## Customization

To add your own categories:

1. Copy this file
2. Add/modify categories in the tables above
3. Update the config.json `categories.taxonomy_file` path

Example custom category:
```markdown
### 🏗️ [YOUR DOMAIN]
| Category | Description | Tags |
|----------|-------------|------|
| `my-category` | What it means | `tag1`, `tag2` |
```
