---
name: scaleway
description: Manage Scaleway cloud infrastructure via the scw CLI — Elastic Metal servers, serverless LLMs (Generative APIs), Kubernetes, databases, object storage, and more. Also covers pi agent integration with Scaleway as an LLM provider.
allowed-tools: Bash(scw:*) Bash(curl:*) Bash(python3:*)
---

# Scaleway Skill

Full management of your Scaleway infrastructure via the `scw` CLI and REST APIs.

## Project Structure

```
scaleway/
├── SKILL.md        # This file
└── pi-setup.md     # Pi agent integration — using Scaleway LLMs inside pi
```

---

## Authentication

Credentials are stored in `~/.config/scw/config.yaml` by the `scw` CLI.

```bash
scw info                        # show current profile, access key, default zone
scw config get secret-key       # retrieve the secret key (use in scripts, never display)
```

> **🔒 Security note**: Never echo or print the secret key. Source it into variables only.

---

## Quick Reference — Your Infrastructure

| Resource | Name | Zone | Status |
|---|---|---|---|
| Elastic Metal | `codimeo.com` | `fr-par-2` | ✅ ready |

---

## Elastic Metal (Bare Metal)

```bash
# List all servers across zones
scw baremetal server list zone=fr-par-1
scw baremetal server list zone=fr-par-2

# Get details of a specific server
scw baremetal server get <server-id> zone=fr-par-2

# List available offers
scw baremetal offer list zone=fr-par-2

# List OS images
scw baremetal os list zone=fr-par-2
```

---

## Serverless LLMs — Generative APIs

### List available models via CLI
```bash
scw inference model list
```

### List via API (more detail)
```bash
curl -s https://api.scaleway.ai/v1/models \
  -H "Authorization: Bearer $(scw config get secret-key)" \
  | python3 -c "
import json, sys
for m in json.load(sys.stdin)['data']:
    print(m['id'], '-', m.get('owned_by',''))
"
```

### Currently available serverless models (Generative APIs — Paris)

| Model ID | Provider | Input (€/M) | Output (€/M) | Vision |
|---|---|---|---|---|
| `mistral-small-3.2-24b-instruct-2506` | Mistral | 0.15 | 0.35 | ✅ |
| `mistral-medium-3.5-128b` | Mistral | 1.50 | 7.50 | ✅ |
| `devstral-2-123b-instruct-2512` | Mistral | 0.40 | 2.00 | — |
| `pixtral-12b-2409` | Mistral | 0.20 | 0.20 | ✅ |
| `voxtral-small-24b-2507` | Mistral | 0.15 | 0.35 | — |
| `llama-3.3-70b-instruct` | Meta | 0.90 | 0.90 | — |
| `qwen3-235b-a22b-instruct-2507` | Qwen | 0.75 | 2.25 | — |
| `qwen3.6-35b-a3b` | Qwen | 0.25 | 1.50 | ✅ |
| `qwen3.5-397b-a17b` | Qwen | 0.60 | 3.60 | ✅ |
| `qwen3-coder-30b-a3b-instruct` | Qwen | 0.20 | 0.80 | — |
| `gpt-oss-120b` | OpenAI | 0.15 | 0.60 | — |
| `gemma-3-27b-it` | Google | 0.25 | 0.50 | ✅ |
| `gemma-4-26b-a4b-it` | Google | 0.25 | 0.50 | ✅ |
| `holo2-30b-a3b` | HCompany | 0.30 | 0.70 | ✅ |
| `glm-5.2` | ZAI | 1.80 | 5.50 | — |
| `bge-multilingual-gemma2` | BAAI | 0.10 | free | — |
| `qwen3-embedding-8b` | Qwen | 0.10 | free | — |
| `whisper-large-v3` | OpenAI | 0.003/min | free | — |

> 💡 **Free tier:** 1 million tokens + 60 min audio included on serverless models.
> 💡 **Batch API:** -50% discount on all serverless prices.

### Call the API directly
```bash
SCW_KEY=$(scw config get secret-key)
curl -s https://api.scaleway.ai/v1/chat/completions \
  -H "Authorization: Bearer $SCW_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-small-3.2-24b-instruct-2506",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 256
  }'
```

### Dedicated deployments (managed inference)
```bash
scw inference deployment list
scw inference deployment create model-id=<model-id> node-type=L4
scw inference node-type list       # show available GPU node types & stock
```

#### Dedicated GPU pricing (Paris)
| Node | GPUs | VRAM | Price/h | ~Price/mo |
|---|---|---|---|---|
| `L4` | 1× L4 | 24 GB | €0.93 | €678 |
| `L40S` | 1× L40S | 48 GB | €1.72 | €1,255 |
| `H100-SXM-2` | 2× H100 | 160 GB | €7.95 | €5,804 |
| `H100-SXM-4` | 4× H100 | 320 GB | €15.22 | €11,111 |
| `H100-SXM-8` | 8× H100 | 640 GB | €30.06 | €21,944 |

---

## Compute Instances

```bash
scw instance server list
scw instance server list zone=fr-par-1
scw instance server create type=DEV1-S image=ubuntu_noble zone=fr-par-1
scw instance server get <server-id>
scw instance server start <server-id>
scw instance server stop <server-id>
```

---

## Kubernetes (Kapsule)

```bash
scw k8s cluster list
scw k8s cluster get <cluster-id>
scw k8s cluster create name=mycluster version=1.32.0 \
  pools.0.size=2 pools.0.node-type=DEV1-M pools.0.name=default
scw k8s kubeconfig get <cluster-id> > ~/.kube/scaleway.yaml
```

---

## Managed Databases

```bash
scw rdb instance list
scw rdb instance get <instance-id>
scw rdb database list instance-id=<instance-id>
scw rdb user list instance-id=<instance-id>
```

---

## Object Storage

```bash
scw object bucket list
scw object bucket create name=my-bucket
scw object object list bucket=my-bucket
```

---

## Networking

```bash
scw vpc private-network list
scw lb lb list
scw dns zone list
scw dns record list dns-zone=example.com
```

---

## Billing

```bash
scw billing invoice list
scw billing consumption list
```

---

## Pi Agent Integration

> See [`pi-setup.md`](./pi-setup.md) for the complete guide on using Scaleway LLMs inside pi.

**Quick summary:**
- Provider already configured in `~/.pi/agent/models.json`
- 15 models available, auto-authenticated via `scw config get secret-key`
- Switch model in pi: type `/model` → search → select

```bash
pi --model mistral-small-3.2-24b-instruct-2506
pi --list-models | grep scaleway
```

---

## Useful Links

- Console: https://console.scaleway.com
- Generative APIs docs: https://www.scaleway.com/en/docs/ai-data/generative-apis/
- CLI reference: https://www.scaleway.com/en/docs/scaleway-cli/
- Status page: https://status.scaleway.com
