# 🚀 Using Scaleway as a Pi Provider

> **TL;DR** — Scaleway's Generative APIs are OpenAI-compatible.
> The config is already added to `~/.pi/agent/models.json`.
> Open `/model` in pi and pick any `scaleway/` model.

---

## How It Works

Scaleway exposes all its serverless LLMs through a single OpenAI-compatible endpoint:

```
https://api.scaleway.ai/v1
```

Authentication uses your **Scaleway Secret Key** as a Bearer token — the same key used by the `scw` CLI.

Pi fetches the key automatically at runtime via:

```json
"apiKey": "!scw config get secret-key"
```

No manual copy-paste. No environment variable to set. As long as `scw` is configured (`scw init`), it just works.

---

## What Was Added to `~/.pi/agent/models.json`

```json
{
  "providers": {
    "scaleway": {
      "name": "Scaleway Generative APIs",
      "baseUrl": "https://api.scaleway.ai/v1",
      "api": "openai-completions",
      "apiKey": "!scw config get secret-key",
      "compat": {
        "supportsDeveloperRole": false,
        "supportsReasoningEffort": false,
        "supportsUsageInStreaming": false,
        "maxTokensField": "max_tokens"
      },
      "models": [ ... ]
    }
  }
}
```

### Why those `compat` flags?

| Flag | Value | Reason |
|---|---|---|
| `supportsDeveloperRole` | `false` | Scaleway doesn't support the OpenAI `developer` role — uses `system` instead |
| `supportsReasoningEffort` | `false` | No `reasoning_effort` param on the Scaleway API |
| `supportsUsageInStreaming` | `false` | Token usage not returned mid-stream |
| `maxTokensField` | `"max_tokens"` | Uses the legacy field name, not `max_completion_tokens` |

---

## Available Models

All 15 models registered, with real pricing (€/million tokens):

| Model ID | Name | Input | Output | Vision |
|---|---|---|---|---|
| `mistral-small-3.2-24b-instruct-2506` | Mistral Small 3.2 | €0.15 | €0.35 | ✅ |
| `mistral-medium-3.5-128b` | Mistral Medium 3.5 | €1.50 | €7.50 | ✅ |
| `devstral-2-123b-instruct-2512` | Devstral 2 123B | €0.40 | €2.00 | — |
| `pixtral-12b-2409` | Pixtral 12B | €0.20 | €0.20 | ✅ |
| `llama-3.3-70b-instruct` | Llama 3.3 70B | €0.90 | €0.90 | — |
| `qwen3-235b-a22b-instruct-2507` | Qwen3 235B | €0.75 | €2.25 | — |
| `qwen3.6-35b-a3b` | Qwen 3.6 35B | €0.25 | €1.50 | ✅ |
| `qwen3.5-397b-a17b` | Qwen 3.5 397B | €0.60 | €3.60 | ✅ |
| `qwen3-coder-30b-a3b-instruct` | Qwen3 Coder 30B | €0.20 | €0.80 | — |
| `gpt-oss-120b` | GPT OSS 120B | €0.15 | €0.60 | — |
| `gemma-3-27b-it` | Gemma 3 27B | €0.25 | €0.50 | ✅ |
| `gemma-4-26b-a4b-it` | Gemma 4 26B | €0.25 | €0.50 | ✅ |
| `holo2-30b-a3b` | Holo2 30B | €0.30 | €0.70 | ✅ |
| `glm-5.2` | GLM 5.2 | €1.80 | €5.50 | — |
| `voxtral-small-24b-2507` | Voxtral 24B (Audio) | €0.15 | €0.35 | — |

> 💡 **Free tier:** Scaleway gives **1 million tokens** free on serverless models.

---

## How to Switch to a Scaleway Model in Pi

### In the TUI
1. Type `/model` in pi
2. Search for the model name (e.g. `mistral-small`)
3. Select it — it will appear under the `scaleway` provider

### From the command line
```bash
pi --model mistral-small-3.2-24b-instruct-2506
pi --model devstral-2-123b-instruct-2512
pi --model llama-3.3-70b-instruct
```

### List all available Scaleway models
```bash
pi --list-models | grep scaleway
```

---

## Adding More Models Later

The Scaleway API is live at `https://api.scaleway.ai/v1/models`. To refresh the list:

```bash
curl -s https://api.scaleway.ai/v1/models \
  -H "Authorization: Bearer $(scw config get secret-key)" \
  | python3 -c "
import json, sys
for m in json.load(sys.stdin)['data']:
    print(m['id'])
"
```

Then add new entries to the `models` array in `~/.pi/agent/models.json`.
The file hot-reloads — no restart needed, just open `/model` again.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Model not appearing in `/model` | Run `scw config get secret-key` — if empty, run `scw init` |
| `401 Unauthorized` | Your SCW secret key may have expired — regenerate in the Scaleway console |
| `403 Forbidden` | Check that your SCW project has the Generative APIs product enabled |
| Model responds but no usage shown | Normal — `supportsUsageInStreaming: false` — cost is tracked post-response |

---

*Config file: `~/.pi/agent/models.json` · API: `https://api.scaleway.ai/v1` · Auth: `scw config get secret-key`*
