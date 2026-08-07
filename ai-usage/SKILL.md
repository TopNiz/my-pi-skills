---
name: ai-usage
description: Check usage, costs, and account status across your AI providers — OpenAI (costs + token usage via admin API key), DeepSeek (balance), Ollama Cloud (model access), and GitHub Copilot (plan + features). API keys read securely from macOS keychain, pi’s auth.json, and opencode config.
---

# AI Usage Checker

Check the status, costs, and usage of all your AI accounts from one place.

| Provider | What's shown |
|---|---|
| **🔵 OpenAI** | 30-day cost, token usage (input/output/cached), request count |
| **🟢 DeepSeek** | Account balance, credited vs topped-up funds |
| **🟠 Ollama Cloud** | API key validity, available cloud models |
| **🐙 GitHub Copilot** | Plan type, features enabled, available models count |
| **🟣 Scaleway** | Total cost by category, AI/Gen APIs highlight, current period consumption |
| **🤖 Codex (ChatGPT)** | Plan, weekly usage limit, reset date, credit balance, estimated credits from local CLI history via the official token-based rate card |

---

## Project Structure

```
ai-usage/
├── SKILL.md                          # This file
├── check-usage.sh                    # Orchestrator — calls provider scripts
└── providers/
    ├── openai.py                     # OpenAI costs + usage
    ├── deepseek.py                   # DeepSeek balance
    ├── ollama.py                     # Ollama Cloud model list
    ├── github_copilot.py             # GitHub Copilot plan + features
    ├── scaleway.py                   # Scaleway cloud costs by category
    └── codex.py                      # Codex (ChatGPT) plan/limits + rate-card credit estimate
```

Each provider script is **standalone** - you can run them individually:

```bash
./providers/openai.py                 # Pretty output
./providers/openai.py --json          # Raw JSON
./providers/openai.py --verbose       # Pretty + raw JSON
./providers/codex.py                  # Codex usage + rate card
./providers/codex.py --json           # JSON only
./providers/codex.py --verbose        # Verbose
```

---

## Setup

### Quick setup (recommended)

Create a `.env` file at `~/.pi/agent/.env` with all your API keys:

```bash
cp .env.example ~/.pi/agent/.env
chmod 600 ~/.pi/agent/.env
# Then edit ~/.pi/agent/.env and fill in your keys
```

The file should contain:

```env
OPENAI_ADMIN_KEY=sk-admin-your-openai-admin-key-here
DEEPSEEK_KEY=sk-your-deepseek-api-key-here
OLLAMA_CLOUD_KEY=your-ollama-cloud-api-key-here
GITHUB_COPILOT_KEY=ghu_your-github-oauth-token-here
```

### OpenAI - Admin API key

OpenAI's [Usage API](https://developers.openai.com/cookbook/examples/completions_usage_api) and [Costs API](https://api.openai.com/v1/organization/costs) require an **Admin API key** (a regular project key won't work).

1. Create an admin key at **OpenAI Dashboard → Settings → Organization → Admin Keys**
   https://platform.openai.com/settings/organization/admin-keys

2. Add it to `~/.pi/agent/.env` under `OPENAI_ADMIN_KEY=`

### Alternative methods (checked in order if .env is missing)

**macOS keychain:**
```bash
security add-generic-password \
  -a "$USER" -s "openai-admin-key" \
  -w "sk-admin-your-key-here" -U
```

**Linux file:**
```bash
mkdir -p ~/.config/openai
echo "sk-admin-your-key-here" > ~/.config/openai/admin-key
chmod 600 ~/.config/openai/admin-key
```

### DeepSeek, Ollama Cloud & GitHub Copilot

Fallback locations if `.env` is not set:

- `~/.pi/agent/auth.json` — DeepSeek (`deepseek.key`)
- `~/.local/share/opencode/auth.json` — Ollama Cloud
- `~/.pi/agent/auth.json` — GitHub Copilot (`github-copilot.refresh`) — *auto-populated when pi authenticates with Copilot*
- `gh auth token` — GitHub Copilot fallback (install `gh` CLI and run `gh auth login`)

---

## Usage

### Check all providers

```bash
./check-usage.sh
```

Output:
```
━━━ AI Usage Report ━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔵 OpenAI (API)
  💰 Cost (30d):  $2.19 USD
    - Default project: $2.1864
  📊 Tokens:     2,288,756 in / 181,172 out / 380,416 cached
  🔄 Requests:   282

🟢 DeepSeek
  💰 Total balance:  $41.85 USD
  ✅ Account:        Active

🟠 Ollama Cloud
  ✅ API key valid - 39 cloud models accessible

🐙 GitHub Copilot
  ✅ Plan:     Individual - Yearly
  ♾️  Quota:    Unlimited (full subscriber)
  🤖 Models:   38 available
  💬 Chat:     enabled
  🕵️  Agent:    enabled
  🔍 Search:   enabled
  🔒 Public code suggestions: disabled

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 For detailed billing:
   OpenAI:           https://platform.openai.com/usage
   DeepSeek:         https://platform.deepseek.com
   Ollama:           https://ollama.com/settings/billing
   GitHub Copilot:   https://github.com/settings/copilot
   Scaleway:         https://console.scaleway.com/billing/invoices
```

### Single provider

```bash
./check-usage.sh openai           # OpenAI only
./check-usage.sh deepseek         # DeepSeek only
./check-usage.sh ollama           # Ollama Cloud only
./check-usage.sh github-copilot   # GitHub Copilot only
./check-usage.sh codex            # Codex (ChatGPT) only
```

### Output modes

```bash
./check-usage.sh                     # Pretty (default)
./check-usage.sh --verbose           # Detailed + raw JSON
./check-usage.sh --json              # Machine-readable JSON
```

### Run a provider script directly

```bash
./providers/openai.py                # Pretty
./providers/openai.py --json         # JSON only
./providers/openai.py --verbose      # Verbose
./providers/scaleway.py              # Scaleway usage
./providers/scaleway.py --json       # JSON only
./providers/scaleway.py --verbose    # Verbose
```

---

## How it works

### OpenAI (`providers/openai.py`)
| Endpoint | Data |
|---|---|
| `GET /v1/organization/usage/completions` | Input/output/cached tokens, request count (30 days) |
| `GET /v1/organization/costs` | Cost by project (30 days) |

Key: macOS Keychain → `openai-admin-key`

### DeepSeek (`providers/deepseek.py`)
| Endpoint | Data |
|---|---|
| `GET /user/balance` | Total balance, granted/topped-up credits, account status |

Key: `~/.pi/agent/auth.json` → `deepseek.key`

### Ollama Cloud (`providers/ollama.py`)
| Endpoint | Data |
|---|---|
| `GET /api/tags` via `https://ollama.com/api` | Available cloud models |

Key: `~/.local/share/opencode/auth.json` → `ollama-cloud.key`

### GitHub Copilot (`providers/github_copilot.py`)

| Endpoint | Data |
|---|---|
| `GET https://api.github.com/copilot_internal/v2/token` | Plan (SKU), features enabled, short-lived access token |
| `GET https://api.githubcopilot.com/models` | Available model list (count + names) |

**Key details:**
- Both endpoints require editor-identity headers: `Editor-Version`, `Editor-Plugin-Version`, `User-Agent` - GitHub blocks requests without them
- The `/copilot_internal/v2/token` endpoint uses `Authorization: token <ghu_...>` (OAuth user token)
- The `/models` endpoint uses `Authorization: Bearer <access_token>` (the short-lived token returned above)
- The access token is short-lived (~30 min); `refresh_in: 1500s` in the response tells clients when to refresh
- There is **no per-user usage/cost API** - Copilot is flat-rate; `limited_user_quotas: null` means unlimited
- The `/user/copilot` REST endpoint returns 404 for individual users - not a valid route
- GraphQL `copilotSubscription` field doesn't exist either

**SKU → plan label mapping:**
| SKU | Label |
|---|---|
| `yearly_subscriber_quota` | Individual - Yearly |
| `monthly_subscriber_quota` | Individual - Monthly |
| `free_subscriber_quota` | Free Tier |
| `business` | Copilot Business |
| `enterprise` | Copilot Enterprise |

**Features reported from the token response:**
`chat_enabled`, `code_review_enabled`, `agent_mode_auto_approval`, `codesearch`, `xcode`, `mcp` (parsed from raw token string)

**Key lookup order:**
1. `GITHUB_COPILOT_KEY` env var / `~/.pi/agent/.env`
2. `~/.pi/agent/auth.json` → `github-copilot.refresh` *(populated automatically by pi when using Copilot)*
3. `gh` CLI - `gh auth token` *(fallback; the regular `gho_...` token also works for this endpoint)*

### Scaleway (`providers/scaleway.py`)

| Endpoint | Data |
|---|---|
| Scaleway CLI `scw billing consumption list` | Monthly consumption by product, aggregated by category |

**How it works:**
- Uses the Scaleway CLI (`scw`) to fetch consumption data via the Billing API v2beta1
- The Go SDK handles HMAC-SHA256 request signing internally, so we can't use plain `curl`
- Consumptions are grouped by category (BareMetal, Object Storage, Compute, Network, etc.)
- AI/Generative API costs are highlighted separately (LLM, gen, chat, embedding, model keywords)
- Currency: EUR

**Credentials:**
- Reads from Scaleway SDK config file: `~/.config/scw/config.yaml`
- Environment variables: `SCW_ORGANIZATION_ID`, `SCW_ACCESS_KEY`, `SCW_SECRET_KEY`

### Codex — ChatGPT product (`providers/codex.py`)

| Endpoint / Source | Data |
|---|---|
| `GET https://chatgpt.com/backend-api/codex/usage` | Plan, weekly limit window (used %, reset date), credit balance, spend control |
| `~/.codex/state_5.sqlite` (threads table) | Per-session token usage by model from local Codex CLI history |
| Official Codex rate card (`help.openai.com/en/articles/20001106`) | Credits per 1M tokens (input/cached/output) per model — token-based pricing since Apr 2026 |

**How it works:**
- Reads the ChatGPT access token from `~/.codex/auth.json` (never printed) and calls the backend API for live plan/limit/credit status
- Computes an **estimated credit consumption** from local CLI history (last 30 days): tokens per model × rate-card credits, using an assumed input/cached/output mix (`SPLIT` constant, default 80/10/10)
- Reports both the estimate and a range (all-cached → all-output) since the local history has no per-request token split
- Token-based rate card is embedded in the script and dated — refresh it when OpenAI publishes updates

**Notes from the official page:**
- No charge for cache writes; fast mode consumes credits at a higher rate
- Code review uses GPT-5.3-Codex; typical GPT-5.6-Sol task ≈ 5–40 credits; avg cost ~$100–200/dev/month
- Codex, ChatGPT Work, ChatGPT for Excel, and Workspace Agents share the same agentic usage/credit pool when available on the plan

---

## Extending

Adding a new provider = adding one Python file:

1. Create `providers/newprovider.py` with the same interface:
   - No args → pretty output to stdout
   - `--json` → raw JSON to stdout
   - `--verbose` → pretty + raw JSON
   - Errors → stderr, exit 1

2. Register it in `check-usage.sh` by adding to the `PROVIDER_SCRIPTS` array.

That's it - the orchestrator handles the rest.
