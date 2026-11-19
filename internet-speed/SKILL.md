---
name: internet-speed
description: Measure separate download and upload capacity to Codimeo, then HTTP responsiveness under simultaneous load; cross-check doubtful macOS results with networkQuality.
---

# Internet speed

Run `scripts/measure.py --json` when the user asks to measure or troubleshoot connectivity. Every Codimeo speed test must separate capacity from responsiveness under load. The script enforces this sequence:

1. Measure idle endpoint HTTP response timing.
2. Measure download capacity with download-only flows; wait for all flows to finish.
3. Measure upload capacity with upload-only flows; wait for all flows to finish.
4. Run a distinct simultaneous download/upload phase and probe endpoint HTTP responsiveness during that load.

Several parallel flows within one direction are allowed. Never overlap the two capacity directions, report simultaneous-load throughput as capacity, or substitute simultaneous rates when capacity is unavailable. Do not diagnose a Wi-Fi, ISP or server fault solely from differences between the two workloads.

## Interpret and present the data

Top-level `download_mbps` and `upload_mbps` are the separate-direction capacity results. `throughput_mode` is `sequential_capacity`, and `capacity_phase_seconds` records each capacity phase's duration. `capacity_samples.download` and `.upload` contain real interval samples `{seconds, mbps, bytes}` for speed-over-time charts. Samples are based on received download bytes and client HTTP upload write progress (`sample_basis` describes this), not an invented animation. Final capacity averages are actual received download bytes or server-confirmed upload bytes divided by direction elapsed time, not the requested volume or the mean of sampled rates. Planned 10-second cutoffs are valid measurements, not failed flows; never substitute buffered upload progress for the server's partial-byte receipt. Use `--` for not measured yet and explicitly unavailable readings for failed flows. `simultaneous_load` contains the separate both-active throughput and duration; it must be visibly distinguished from capacity. `http_response_ms` is idle endpoint timing and `loaded_http_response_ms` is timing during the simultaneous-load phase. A direction with any genuine failed flow is unavailable. Intentional deadline cancellation is normal only when its actual byte count is verified.

Choose presentation to fit the agent's interface:

- In a terminal, present a concise table or bullets with capacity prominently labeled as measured separately, simultaneous-load rates separately labeled, idle/loaded HTTP median and p95, failed probe rates, flow count, timestamp, endpoint, route and errors.
- In an app that supports inline visualizations, craft a compact interactive visual from this run's JSON using the available in-conversation visualization capability. Show capacity prominently, distinguish simultaneous-load results, and keep timing, failures, timestamp, route and errors available as context. Follow the user's requested display format. Build the visual live; do not direct the user to a prebuilt dashboard.

Treat capacity as bounded throughput to Codimeo, not a definitive line-capacity rating. HTTP response timing includes request and connection setup and is not raw network RTT. Response-time variation is not packet jitter, and failed HTTP probes are not packet loss. Do not invent quality scores or missing results.

## Independent comparison

If an unexpected result needs a macOS cross-check, match the workload: `networkQuality -s -c` measures separate directions for a capacity comparison; `networkQuality -c` runs upload/download simultaneously for a load comparison. Apple's tool uses different endpoints and methods, so label it an independent cross-check. Convert its throughput from bits/second to Mbps by dividing by 1,000,000; report `base_rtt` in milliseconds separately from Codimeo HTTP timing. On Linux and Windows, use the Codimeo client without requiring Apple's utility.

## Bounds and service

The public site at `https://speed-test.chain-it.com/` retains its approved web UI at `/` and serves the API at its existing paths. A separate development UI runs at `http://127.0.0.1:63035/`, using an explicit remote API URL rather than measuring localhost. Developing locally does not authorize removing or replacing the public UI; UI publication requires explicit user approval. The installed client uses the public API URL by default; the former Codimeo speed-test hostname is not an alias. The endpoint provides `/capabilities`, `/ping`, `/download?bytes=N`, `/upload`, and `/upload-receipt/{id}`; use `--endpoint URL` or `SPEEDTEST_ENDPOINT` to override it. The adaptive client requires capability protocol version 1 and fails clearly against older servers. Each transfer request is bounded at exactly 1,000,000,000 bytes.

Download and upload each have ONE 10-second window. Start at 70 MB. After completing a stage, compute `estimated_next_seconds = next_preset_bytes / (confirmed_bytes_so_far / elapsed_seconds)`. Automatically add the next FULL preset (300 MB, then 1 GB) only if this estimate fits the remaining time. Do not reset the deadline or apply an arbitrary two-second/Mbps threshold. Stop when the deadline is reached, the next preset will not fit, or the largest allowed preset is complete. If conditions worsen after escalation, the same deadline still stops the transfer normally. Directions adapt independently; preset totals split across flows rather than multiply by flow count.

Default automatic escalation permits all presets. `--max-size-mb 70`, `300`, or `1000` sets the maximum stage. Stages are cumulative: 70 MB plus a full 300 MB is 370 MB, not 300 MB total. The separate simultaneous-load phase uses at most 70 MB per direction within its own shared 10-second window. Worst-case full-test payload budgets are 280 MB, 880 MB, and 2.88 GB respectively, excluding overhead. Disclose the maximum before running; a user-requested small-data test should cap escalation at 70 MB. Automatic stages belong to this one bounded run, not background or repeated tests.

Adaptive transfers stop at the single direction deadline, even midway through a preset. Download counts come from actually received bytes. Uploads are cancelled at the deadline, then a separately bounded receipt check confirms what the server received; this short verification can add elapsed time without extending the transfer window. Missing or invalid receipts make upload unavailable. Genuine network, HTTP and integrity failures are not successful cutoffs. `capacity_bytes`, `capacity_stages` and `capacity_stop_reason` explain actual volumes and stop decisions. Downloads are read and discarded in 64 KiB blocks, without saving a file. Uploads are generated in bounded blocks. There is no downloaded file to delete, and there are no full-size payload buffers. Numeric chart samples remain only in the current result. Explicit fixed `--size-mb` and paired legacy `--download-mib`/`--upload-mib` remain only for deliberate diagnostic or CI compatibility; they cannot be mixed with `--max-size-mb`. Do not select fixed-volume mode for a normal adaptive user test.

The browser UI starts with two-dash placeholders and live time-series charts. Browser upload samples are browser-reported progress; CLI upload samples describe client socket writes. Final upload averages require complete acknowledgements or verified partial-upload receipts; live progress alone is insufficient. Do not label live samples as definitive instantaneous line speed.

Larger presets require the updated API and host Nginx body limit/timeouts. The image deployment alone does not update Nginx. The service documents explain capability protocol 1, receipt routing, the required 1 GB API limit, `1000m` Nginx body allowance, burst 120 (including CORS preflights), and compatibility-mode idle timeouts. Browser access is limited to exact `SPEEDTEST_ALLOWED_ORIGINS` entries for the local preview; no wildcard or credentialed CORS is enabled. CLI requests without Origin remain supported. Server receipt counters are memory-only, capped at 1024, and expire after 30 seconds; no payloads or client addresses are saved. If the deployed server rejects a preset, report it as unavailable rather than silently reducing the selected size.

Use results for that run only. Do not save measurement history, repeat tests, or run background measurements unless the user asks. Treat endpoint failures as unavailable measurements. Do not infer the user's public IP or location unless explicitly requested.

## Deploy your own server

The server source is maintained in [TopNiz/internet-speedtest on GitHub](https://github.com/TopNiz/internet-speedtest). Users with repository access can clone or fork it and deploy their own FastAPI speed-test server as a Docker container. Follow the repository's `README.md` and `deployment.md`; adapt the hostname, registry/image destination and deployment settings to the user's infrastructure. Keep credentials in external secret storage, such as GitHub Actions secrets, rather than in the shared skill or source files.

Point the installed client at the user's server with its base URL:

```sh
python3 scripts/measure.py --endpoint https://speedtest.example.net --json
```

Alternatively, set the endpoint for the invocation through the environment:

```sh
SPEEDTEST_ENDPOINT=https://speedtest.example.net python3 scripts/measure.py --json
```

Run these commands from the skill directory, or resolve `scripts/measure.py` relative to this `SKILL.md`. The base URL must expose `/ping`, `/download?bytes=N` and `/upload`; both capacity and simultaneous-load phases use the configured endpoint. An explicit `--endpoint` takes precedence over `SPEEDTEST_ENDPOINT`.

For the bundled service contract and container files, read `service/README.md` and use the source in `service/`.
