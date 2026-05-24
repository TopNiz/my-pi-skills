# Ollama Cloud Models — Availability Report

Server: `http://localhost:11434/v1`
Tested: 2026-05-18

## ✅ Free models (34)

| Model | Notes |
|---|---|
| `gemma3:27b-cloud` | |
| `gemma3:12b-cloud` | |
| `gemma3:4b-cloud` | |
| `gemma4:31b-cloud` | |
| `qwen3-coder-next:cloud` | |
| `qwen3-coder:480b-cloud` | |
| `qwen3-vl:235b-instruct-cloud` | |
| `qwen3-vl:235b-cloud` | |
| `qwen3-next:80b-cloud` | |
| `cogito-2.1:671b-cloud` | |
| `nemotron-3-super:cloud` | reasoning model |
| `nemotron-3-nano:30b-cloud` | |
| `minimax-m2:cloud` | reasoning model |
| `minimax-m2.1:cloud` | reasoning model |
| `minimax-m2.5:cloud` | reasoning model |
| `gpt-oss:20b-cloud` | reasoning model |
| `gpt-oss:120b-cloud` | reasoning model |
| `rnj-1:8b-cloud` | |
| `devstral-2:123b-cloud` | |
| `devstral-small-2:24b-cloud` | |
| `ministral-3:14b-cloud` | |
| `ministral-3:8b-cloud` | |
| `ministral-3:3b-cloud` | |
| `glm-4.7:cloud` | reasoning model |
| `glm-4.6:cloud` | reasoning model |
| `minimax-m2:cloud` | |
| `minimax-m2.1:cloud` | |
| `minimax-m2.5:cloud` | |
| `nemotron-3-super:cloud` | |
| `nemotron-3-nano:30b-cloud` | |
| `qwen3-vl:235b-instruct-cloud` | |
| `qwen3-vl:235b-cloud` | |
| `gpt-oss:20b-cloud` | |
| `gpt-oss:120b-cloud` | |

## ❌ Paid models — 403 Subscription required (17)

| Model | Error |
|---|---|
| `glm-5:cloud` | requires a subscription |
| `glm-5.1:cloud` | requires a subscription |
| `minimax-m2.7:cloud` | requires a subscription |
| `deepseek-v3.2:cloud` | requires a subscription |
| `deepseek-v3.1:671b-cloud` | requires a subscription |
| `deepseek-v4-pro:cloud` | requires a subscription |
| `deepseek-v4-flash:cloud` | requires a subscription |
| `kimi-k2-thinking:cloud` | requires a subscription |
| `kimi-k2:1t-cloud` | requires a subscription |
| `kimi-k2.5:cloud` | requires a subscription |
| `kimi-k2.6:cloud` | requires a subscription |
| `gemini-3-flash-preview:cloud` | requires a subscription |
| `qwen3.5:cloud` | requires a subscription |
| `qwen3.5:397b-cloud` | requires a subscription |
| `mistral-large-3:675b-cloud` | requires a subscription |

## Related Nextcloud config

The `integration_openai` app (v4.4.0) is configured to use this Ollama endpoint:

- URL: `http://localhost:11434/v1`
- Service name: `Ollama`
- Default completion model: `glm-5.1:cloud` **(PAID — needs to be changed)**
- Default image model: `flux.2-klein-9b`

The `llm2` ExApp (v2.7.0) runs local models (Olmo-3-7B-Instruct, Qwen2.5-7B, etc.) on codimeo.com.
