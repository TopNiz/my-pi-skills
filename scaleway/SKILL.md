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
├── .env            # Container Registry pull credential (owner readable only)
├── SKILL.md        # This file
└── pi-setup.md     # Pi agent integration — using Scaleway LLMs inside pi
```

---

## Authentication

Credentials are stored in `~/.config/scw/config.yaml` by the `scw` CLI. This is a
personal key with full user rights, so prefer a scoped IAM application key for
anything that runs unattended.

```bash
scw info                        # show current profile, access key, default zone
scw config get secret-key       # retrieve the secret key (use in scripts, never display)
```

> **🔒 Security note**: Never echo or print the secret key. Source it into variables only.

---

## Container Registry

The registry lives in `fr-par`, the same region as `codimeo.com`, so images
never leave the region on their way to the server.

| Item | Value |
|---|---|
| Endpoint | `rg.fr-par.scw.cloud` |
| Namespace | `chain-it` (private) |
| Namespace id | `0fc6eca8-bccb-458a-afdc-6e35f2be7504` |
| Website image | `rg.fr-par.scw.cloud/chain-it/chain-it-website` |
| Tags | `prod` (moving), `sha-<commit>`, `<date>-<sha>` (immutable) |

### Credentials

Two IAM applications, each with a policy scoped to the project, so neither uses
a personal key:

| Application | Policy / permission set | Holder |
|---|---|---|
| `chain-it-ci` | `chain-it-ci-push` / `ContainerRegistryFullAccess` | GitHub Actions secrets `SCW_ACCESS_KEY`, `SCW_SECRET_KEY` in `TopNiz/chain-it-website` |
| `chain-it-server-pull` | `chain-it-server-pull` / `ContainerRegistryReadOnly` | this skill's `.env`, used by `codimeo.com` |

`.env` variables (owner readable only, `chmod 600`):

| Variable | Purpose |
|---|---|
| `SCW_REGISTRY` | Registry endpoint, `rg.fr-par.scw.cloud` |
| `SCW_REGISTRY_NAMESPACE` | Namespace, `chain-it` |
| `SCW_REGISTRY_ACCESS_KEY` | Pull credential, access key (this is the docker username) |
| `SCW_REGISTRY_SECRET_KEY` | Pull credential, secret key (this is the docker password) |

> **🔒 Security note**: never echo, print, log or commit these values, and never
> pass them as command arguments. Source the file into variables and pipe the
> secret into `docker login --password-stdin`.

### Log in, log out, verify

```bash
set -a; . ~/.agents/skills/scaleway/.env; set +a

# Log in without putting the secret on the command line
printf '%s' "$SCW_REGISTRY_SECRET_KEY" \
  | docker login "$SCW_REGISTRY" --username "$SCW_REGISTRY_ACCESS_KEY" --password-stdin

# Verify: pull the published site image (the server is amd64)
docker pull "$SCW_REGISTRY/$SCW_REGISTRY_NAMESPACE/chain-it-website:prod"

# Log out and clear the variables
docker logout "$SCW_REGISTRY"
unset SCW_REGISTRY_SECRET_KEY SCW_REGISTRY_ACCESS_KEY
```

On `codimeo.com` this login is already in place, stored in
`~/.docker/config.json`. Re-run the commands above only after rotating the key.
The pull credential cannot push: an attempted `docker push` is denied.

### Inspecting and pruning

In this API an *image* is the repository and *tags* are the versions. Never run
`scw registry image delete`: it removes the repository and every tag in it.

```bash
scw registry namespace list
scw registry image list namespace-id=0fc6eca8-bccb-458a-afdc-6e35f2be7504 -o json  # one entry per repository
scw registry tag list image-id=<image-id> -o json                             # tags, with digests

# remove one version
scw registry tag delete tag-id=<tag-id>
# tags sharing a digest need the deprecated flag, or the call fails
scw registry tag delete force=true tag-id=<tag-id>
```

Old dated tags accumulate at roughly 80 MB each. Keep the deployed tag and the one
before it, and always delete the tag, never the image.

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

## Organization Quota API

Scaleway's IAM Quotas API provides organization quota limits and locality
(global, region, or zone). It has two read-only calls:

```bash
SCW_SECRET_KEY="$(scw config get secret-key)"
SCW_ORG_ID="$(scw config get default-organization-id)"

# List all quotas and their per-locality limits
curl -sS -G 'https://api.scaleway.com/iam/v1alpha1/quota' \
  --data-urlencode "organization_id=$SCW_ORG_ID" \
  -H "X-Auth-Token: $SCW_SECRET_KEY"

# Retrieve one quota by its exact quota name
curl -sS -G 'https://api.scaleway.com/iam/v1alpha1/quota/<quotum_name>' \
  --data-urlencode "organization_id=$SCW_ORG_ID" \
  -H "X-Auth-Token: $SCW_SECRET_KEY"

unset SCW_SECRET_KEY SCW_ORG_ID
```

Keep the secret key out of terminal output, logs, and source control. The list
response includes quota names, limits, and locality fields such as `global`,
`region`, or `zone`. See the [IAM Quotas API reference](https://www.scaleway.com/en/developers/api/iam/quotas).

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

## Resource-scoped cost estimation and billing reconciliation

For general cost or monthly billing requests, list the cost items first, then offer details on a selected item. Do not require an Instance ID before showing the billing overview. Reuse the code below instead of rebuilding billing or pricing lookups for each request. Cost inspection is read-only; it never authorizes provisioning, shutdown, deletion, or changes to local files.

### Default workflow: cost items first, details on request

1. Use the requested billing month and year. Resolve an unclear year from conversation context or ask. Use the existing `scw` login and configured organization; no CRM, spawner, `.env` or custom project configuration is needed.
2. For an organization-wide request, query monthly consumption without a project filter and retrieve all pages. Do not silently use `scw billing consumption list` defaults: the CLI can apply its default project and omit other projects.
3. Present a concise table of product/cost items with amounts and currency before tax. Include negative deductions/credits. Report zero-cost items, either in the table or in a separate short list.
4. Show the subtotal, provider-reported taxes when available, and the total including tax. Do not recalculate tax from a percentage: provider line-level rounding can produce a different amount. If tax lookup fails, say it is unavailable rather than inventing zero.
5. State the organization/project scope and billing period. Label the amounts as recorded consumption, not a price estimate or final invoice; billing can lag. Do not expose credentials or operational IDs.
6. End with: **"Would you like more detail on one item, for example a past or running instance?"** Then wait. Do not automatically inventory servers, inspect project files, or run per-Instance estimates after listing costs.
7. Once the user selects an item, use the detail workflow below. Ask for a resource name/ID only if the selected billing item does not identify a unique resource. An explicit request for details on an already named resource counts as selection; keep that lookup scoped rather than listing unrelated organization costs.

**Attribution limit:** Monthly billing includes consumption from both past and current resources, but the returned cost items are often aggregated product/SKU totals. They are not a complete inventory of individual past and running Instances. Never claim that one DEV1-M billing line identifies one VM, or that all historical VM identities can be recovered from it. Deleted-resource details require saved inventory, usage history, or other available billing evidence. Do not recreate a resource to obtain an estimate.

### Reusable organization-wide monthly cost listing

Replace `YYYY-MM` with the requested period. This reads billing only, uses the configured `scw` organization, and applies no project filter. Format the returned cost items as a table and ask the follow-up question above; do not proceed to resource inspection without selection.

```bash
python3 - YYYY-MM <<'PY'
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from decimal import Decimal


def cli(*args):
    result = subprocess.run(
        ['scw', *args], capture_output=True, text=True, timeout=60,
    )
    if result.returncode or not result.stdout.strip():
        raise ValueError('CLI lookup failed')
    return result.stdout.strip()


def money(value):
    return Decimal(str(value.get('units', 0))) + (
        Decimal(str(value.get('nanos', 0))) / Decimal(10**9)
    )


try:
    period = sys.argv[1]
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', period):
        raise ValueError('Expected YYYY-MM')
    organization = cli('config', 'get', 'default-organization-id')
    secret = cli('config', 'get', 'secret-key')
    rows = []
    for page in range(1, 101):
        query = urllib.parse.urlencode({
            'organization_id': organization, 'billing_period': period,
            'page': page, 'page_size': 100,
        })
        request = urllib.request.Request(
            'https://api.scaleway.com/billing/v2beta1/consumptions?' + query,
            headers={'X-Auth-Token': secret, 'Accept': 'application/json'},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.load(response, parse_float=Decimal)
        batch = payload['consumptions']
        rows.extend(batch)
        count = payload.get('total_count')
        if count is not None and len(rows) >= int(count):
            break
        if len(batch) < 100:
            if count is not None and len(rows) < int(count):
                raise ValueError('Incomplete billing pagination')
            break
    else:
        raise ValueError('Billing pagination limit exceeded')
    grouped = defaultdict(Decimal)
    totals = defaultdict(Decimal)
    for row in rows:
        value = row['value']
        currency = value['currency_code']
        amount = money(value)
        key = (row.get('category_name', 'Other'),
               row.get('product_name', 'Unnamed'),
               row.get('resource_name', ''), currency)
        grouped[key] += amount
        totals[currency] += amount
    print(f'Recorded consumption for {period}; configured organization, all projects.')
    for (category, product, description, currency), amount in sorted(grouped.items()):
        print(json.dumps({'category': category, 'item': product,
                          'description': description, 'amount': str(amount),
                          'currency': currency}, ensure_ascii=False))
    for currency, subtotal in sorted(totals.items()):
        print(f'Subtotal before tax: {subtotal:.2f} {currency}')
    try:
        payload = json.loads(cli('billing', 'consumption', 'list-taxes',
                                f'organization-id={organization}',
                                f'billing-period={period}', '-o', 'json'),
                             parse_float=Decimal)
        taxes = payload['taxes'] if isinstance(payload, dict) else payload
        if not taxes:
            raise ValueError('No tax lines returned')
        tax_totals = defaultdict(Decimal)
        for tax in taxes:
            value = tax['total_tax_value']
            amount = money(value) if isinstance(value, dict) else Decimal(str(value))
            currency = tax['currency']
            tax_totals[currency] += amount
            rate = Decimal(str(tax['rate'])) * 100
            print(f'Provider-reported tax ({rate}%): {amount:.2f} {currency}')
        for currency, subtotal in sorted(totals.items()):
            if currency in tax_totals:
                print(f'Total including tax: {subtotal + tax_totals[currency]:.2f} {currency}')
            else:
                print(f'Tax amount unavailable for {currency}; no tax-inclusive total.')
    except Exception:
        print('Tax amount unavailable; subtotals exclude tax.')
    print('Recorded consumption can lag and is not a final invoice.')
except Exception:
    raise SystemExit('Monthly cost lookup failed; verify period and CLI access. '
                     'No credentials or raw provider diagnostics displayed.') from None
PY
```

### Item detail workflow (after selection)

1. Identify the exact approved project, zone, service and resource IDs. Verify ownership before any separately authorized decommission.
2. Before deletion or inventory scrubbing, capture resource creation timestamps, actual disk sizes in bytes, VM power history if available, and the start/end of each billable allocation. Keep operational IDs private. Do not assume the planned disk size equals the allocated size.
3. Fetch current public retail prices once with `scw product-catalog product list zone=<instance-zone> -o json`. Capture and parse the output; select exact SKUs. Filtering only by Instance/Block Storage product type can omit local SSD and IPv4 prices.
4. When requested, read consumption with `scw billing consumption list project-id=<instance-project> billing-period=YYYY-MM -o json`. Derive the project from the inspected Instance, not from a project-specific config file. Keep this separate from the resource-specific estimate.
5. Report the runtime, component estimates, currency, tax treatment, rate source and any billing limitations. Prefer a concise answer. Do not delay an authorized cleanup while researching billing.

### Calculation and attribution rules

- Convert Scaleway money using `Decimal(units) + Decimal(nanos) / 1_000_000_000`. Do not use binary floating point for money.
- Convert provider storage sizes to decimal GB using `bytes / 1_000_000_000`, not GiB. Multiply each quantity by its verified unit price and billable duration. Round the final currency total once.
- VM compute, boot storage, Block Storage and reserved IPv4 are separate chargeable components. VM poweroff does not end storage/IP allocation charges. Include other owned chargeable resources if present.
- Confirm the price's billing cadence as well as its quantity unit. For the template below, compute is per hour, local SSD and SBS 5K/15K are per GB-hour, and flexible IPv4 is per IP-hour. Catalog quantity units can say only `gigabyte` or `ip`; do not infer the time basis from that label alone.
- Current catalog prices give a retail estimate, not a historical invoice. Rate changes, discounts, credits, provider rounding, taxes and other chargeable resources can change the final amount. Do not reuse old plan prices without checking them.
- Use each resource's actual billable interval when available. A common allocation-to-cleanup interval is only an approximation; compute can stop earlier, and a disk/IP can be allocated before VM creation. Record that limitation.
- Monthly consumption can combine several runs and unrelated resources with the same SKU. A field named `consumer_id` is not proof of a per-resource charge. Unless exact resource attribution is established, label the result as a project/month product total, never as this Instance's actual cost.
- Do not infer hourly prices from rounded monthly amounts or blindly interpret consumption quantity/unit labels. Use the product catalog and documented billing semantics. Repeat monthly queries when a run crosses billing periods.
- Explicitly distinguish **estimated resource cost**, **recorded monthly consumption**, and **final invoiced amount**. Billing can lag behind deletion. Never claim zero cost merely because resources are absent.

### Portable Instance estimator: no project files

Use the self-contained code below from any directory. It needs Python 3 and an authenticated `scw` CLI only. It does not read CRM files, `.env` files, a spawner repository, or custom environment variables.

Replace `INSTANCE_ID` with the exact approved Instance UUID. The zone defaults to the existing `scw` configuration; add `--zone fr-par-1` if needed. `--hours` defaults to a 24-hour continuous-running projection. Set a different duration for another projection or a known historical interval. Add `--billing-period YYYY-MM` only when project/month consumption is also requested.

The code discovers the Instance type, project, attached disk sizes/classes, and attached public IPv4 count through read-only provider calls. It supports local SSD and SBS 5K/15K volumes. It rejects unsupported storage or missing/ambiguous prices rather than silently omitting charges. Unattached resources, snapshots, backups, bandwidth and other services are outside this attached-resource estimate.

**Limits:** A deleted Instance cannot be inspected. Historical estimates then require saved resource quantities and billable intervals. Current metadata does not reconstruct prior power states, resizing or rate changes. There is no universal exact-cost calculation without that history; never present a projection as a final invoice.

```bash
python3 - INSTANCE_ID --hours 24 <<'PY'
import argparse
import ipaddress
import json
import re
import subprocess
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID


def scw_json(*args):
    result = subprocess.run(
        ['scw', *args, '-o', 'json'],
        capture_output=True, text=True, timeout=90,
    )
    if result.returncode:
        raise ValueError('Provider lookup failed')
    return json.loads(result.stdout)


def money(value):
    return Decimal(str(value.get('units', 0))) + (
        Decimal(str(value.get('nanos', 0))) / Decimal(10**9)
    )


parser = argparse.ArgumentParser(description='Read-only Instance retail estimate')
parser.add_argument('instance_id')
parser.add_argument('--zone')
parser.add_argument('--hours', default='24')
parser.add_argument('--billing-period')
args = parser.parse_args()
try:
    instance_id = str(UUID(args.instance_id))
    hours = Decimal(args.hours)
    if not hours.is_finite() or hours <= 0:
        raise ValueError('Positive finite duration required')
    if args.billing_period and not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', args.billing_period):
        raise ValueError('Invalid billing period')
    zone_arg = [f'zone={args.zone}'] if args.zone else []
    payload = scw_json('instance', 'server', 'get', instance_id, *zone_arg)
    server = payload.get('server', payload)
    if server['id'] != instance_id:
        raise ValueError('Instance identity mismatch')
    zone = server['zone']
    if args.zone and zone != args.zone:
        raise ValueError('Instance zone mismatch')
    project = str(UUID(server.get('project') or server['project_id']))
    payload = scw_json('product-catalog', 'product', 'list', f'zone={zone}')
    products = payload['products'] if isinstance(payload, dict) else payload
    compute = [p for p in products if
               ((p.get('properties') or {}).get('instance') or {}).get('offer_id')
               == server['commercial_type']]
    if len(compute) != 1:
        raise ValueError('Compute price missing or ambiguous')
    components = [('Compute', compute[0]['sku'], Decimal(1), 'hour')]
    disks = server['volumes']
    if not disks or len({v['id'] for v in disks.values()}) != len(disks):
        raise ValueError('Missing or ambiguous disk inventory')
    for disk in disks.values():
        kind = disk['volume_type']
        if kind == 'l_ssd':
            size = Decimal(str(disk['size'])) / Decimal(10**9)
            sku = f'/instance/volume/l_ssd/{zone}'
            label = 'Local SSD'
        elif kind == 'sbs_volume':
            payload = scw_json('block', 'volume', 'get', disk['id'], f'zone={zone}')
            volume = payload.get('volume', payload)
            if volume['id'] != disk['id'] or volume['project_id'] != project:
                raise ValueError('Block volume identity/project mismatch')
            tier = {5000: '5k', 15000: '15k'}.get(volume['perf_iops'])
            if tier is None:
                raise ValueError('Unsupported Block Storage performance class')
            size = Decimal(str(volume['size'])) / Decimal(10**9)
            sku = f'/storage/block/volume-low-latency-{tier}/{zone}'
            label = f'SBS {tier.upper()}'
        else:
            raise ValueError('Unsupported disk type')
        if not size.is_finite() or size <= 0:
            raise ValueError('Invalid disk size')
        components.append((f'{label} ({size} GB)', sku, size, 'gigabyte'))
    addresses = list(server.get('public_ips') or [])
    if server.get('public_ip'):
        addresses.append(server['public_ip'])
    ipv4 = {ip['address'] for ip in addresses
            if ipaddress.ip_address(ip['address']).version == 4}
    if ipv4:
        components.append(('Public IPv4', f'/network/ipam/ipv4/{zone}',
                           Decimal(len(ipv4)), 'ip'))
    lines = []
    total = Decimal(0)
    currency = None
    for label, sku, quantity, unit in components:
        matches = [p for p in products if p.get('sku') == sku]
        if len(matches) != 1:
            raise ValueError('Price missing or ambiguous')
        product = matches[0]
        measure = product['unit_of_measure']
        scale = Decimal(str(measure['size']))
        if measure['unit'] != unit or not scale.is_finite() or scale <= 0:
            raise ValueError('Verify price units before estimating')
        price = product['price']['retail_price']
        code = price['currency_code']
        if currency is not None and currency != code:
            raise ValueError('Mixed currencies')
        currency = code
        rate = money(price) / scale
        if not rate.is_finite() or rate < 0:
            raise ValueError('Invalid price')
        cost = rate * quantity * hours
        total += cost
        lines.append(f'{label}: {cost:.6f} {currency}, estimated before tax')
    print('\n'.join(lines))
    rounded = total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    print(f'Estimated total for {hours} continuous-running hours: '
          f'{rounded} {currency} before tax')
    print('Current attached resources and current retail rates; not a final invoice.')
    if args.billing_period:
        try:
            payload = scw_json('billing', 'consumption', 'list',
                               f'project-id={project}',
                               f'billing-period={args.billing_period}')
            rows = payload['consumptions'] if isinstance(payload, dict) else payload
            skus = {sku for _, sku, _, _ in components}
            print(f'Project/month consumption ({args.billing_period}):')
            for row in rows:
                if row.get('sku') in skus:
                    value = row['value']
                    print(f"{row['product_name']}: {money(value):.2f} "
                          f"{value['currency_code']}")
            print('Monthly amounts are not attributed to this Instance alone.')
        except Exception:
            print('Monthly billing lookup failed; estimate is not an invoice.')
except Exception:
    raise SystemExit('Estimation failed: verify Instance ID/zone, access, '
                     'duration, supported storage and catalog prices. '
                     'No credentials or raw provider diagnostics displayed.') from None
PY
```

Capture provider subprocess output rather than forwarding raw errors. Never print environment dumps, authentication headers, credentials or private run identifiers. Missing or ambiguous prices must stop the estimate rather than silently use an old rate.

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
