---
name: internet-connection-check
description: Measure separate download and upload capacity to Codimeo, then HTTP responsiveness under simultaneous load; cross-check doubtful macOS results with networkQuality.
---

# Internet connection check

Run `scripts/measure.py --json` when the user asks to measure or troubleshoot connectivity. Every Codimeo speed test must separate capacity from responsiveness under load. The script enforces this sequence:

1. Measure idle endpoint HTTP response timing.
2. Measure download capacity with download-only flows; wait for all flows to finish.
3. Measure upload capacity with upload-only flows; wait for all flows to finish.
4. Run a distinct simultaneous download/upload phase and probe endpoint HTTP responsiveness during that load.

Several parallel flows within one direction are allowed. Never overlap the two capacity directions, report simultaneous-load throughput as capacity, or substitute simultaneous rates when capacity is unavailable. Do not diagnose a Wi-Fi, ISP or server fault solely from differences between the two workloads.

## Interpret and present the data

Top-level `download_mbps` and `upload_mbps` are the separate-direction capacity results. `throughput_mode` is `sequential_capacity`, and `capacity_phase_seconds` records each capacity phase's duration. `simultaneous_load` contains the separate both-active throughput and duration; it must be visibly distinguished from capacity. `http_response_ms` is idle endpoint timing and `loaded_http_response_ms` is timing during the simultaneous-load phase. A direction with any failed flow is unavailable, not a partial capacity estimate.

Choose presentation to fit the agent's interface:

- In a terminal, present a concise table or bullets with capacity prominently labeled as measured separately, simultaneous-load rates separately labeled, idle/loaded HTTP median and p95, failed probe rates, flow count, timestamp, endpoint, route and errors.
- In an app that supports inline visualizations, craft a compact interactive visual from this run's JSON using the available in-conversation visualization capability. Show capacity prominently, distinguish simultaneous-load results, and keep timing, failures, timestamp, route and errors available as context. Follow the user's requested display format. Build the visual live; do not direct the user to a prebuilt dashboard.

Treat capacity as bounded throughput to Codimeo, not a definitive line-capacity rating. HTTP response timing includes request and connection setup and is not raw network RTT. Response-time variation is not packet jitter, and failed HTTP probes are not packet loss. Do not invent quality scores or missing results.

## Independent comparison

If an unexpected result needs a macOS cross-check, match the workload: `networkQuality -s -c` measures separate directions for a capacity comparison; `networkQuality -c` runs upload/download simultaneously for a load comparison. Apple's tool uses different endpoints and methods, so label it an independent cross-check. Convert its throughput from bits/second to Mbps by dividing by 1,000,000; report `base_rtt` in milliseconds separately from Codimeo HTTP timing. On Linux and Windows, use the Codimeo client without requiring Apple's utility.

## Bounds and service

The default endpoint is `https://speedtest.codimeo.com/`. The endpoint provides `/ping`, `/download?bytes=N`, and `/upload`; use `--endpoint URL` or `SPEEDTEST_ENDPOINT` to override it. Defaults transfer 25 MiB down and 10 MiB up for capacity, then the same amounts for simultaneous load: 70 MiB total. Configured transfer sizes apply to each phase; the maximum CLI settings total 150 MiB. The default flow count is three per active direction.

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
