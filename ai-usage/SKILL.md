---
name: ai-usage
description: Check usage, costs, and account status across your AI providers — OpenAI (costs + token usage via admin API key), DeepSeek (balance), and Ollama Cloud (model access). API keys read securely from macOS keychain, pi's auth.json, and opencode config.
---

# AI Usage Checker

Check the status, costs, and usage of all your AI accounts from one place.

| Provider | What's shown |
|---|---|
| **🔵 OpenAI** | 30-day cost, token usage (input/output/cached), request count |
| **🟢 DeepSeek** | Account balance, credited vs topped-up funds |
| **🟠 Ollama Cloud** | API key validity, available cloud models |

---

## Project Structure

```
ai-usage/
├── SKILL.md                          # This file
├── check-usage.sh                    # Orchestrator — calls provider scripts
└── providers/
    ├── openai.py                     # OpenAI costs + usage
    ├── deepseek.py                   # DeepSeek balance
    └── ollama.py                     # Ollama Cloud model list
```

Each provider script is **standalone** — you can run them individually:

```bash
./providers/openai.py                 # Pretty output
./providers/openai.py --json          # Raw JSON
./providers/openai.py --verbose       # Pretty + raw JSON
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
```

### OpenAI — Admin API key

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

### DeepSeek & Ollama Cloud

Fallback locations if `.env` is not set:

- `~/.pi/agent/auth.json` — DeepSeek
- `~/.local/share/opencode/auth.json` — Ollama Cloud

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
  ✅ API key valid — 39 cloud models accessible

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 For detailed billing:
   OpenAI:    https://platform.openai.com/usage
   DeepSeek:  https://platform.deepseek.com
   Ollama:    https://ollama.com/settings/billing
```

### Single provider

```bash
./check-usage.sh openai       # OpenAI only
./check-usage.sh deepseek     # DeepSeek only
./check-usage.sh ollama       # Ollama Cloud only
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

---

## Extending

Adding a new provider = adding one Python file:

1. Create `providers/newprovider.py` with the same interface:
   - No args → pretty output to stdout
   - `--json` → raw JSON to stdout
   - `--verbose` → pretty + raw JSON
   - Errors → stderr, exit 1

2. Register it in `check-usage.sh` by adding to the `PROVIDER_SCRIPTS` array.

That's it — the orchestrator handles the rest.
