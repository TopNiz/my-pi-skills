#!/usr/bin/env python3
"""Measure Codimeo capacity in separate directions, then responsiveness under simultaneous load."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import json
import os
import platform
import statistics
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlsplit


def request(url, method="GET", data=None, timeout=20):
    req = urllib.request.Request(url, data=data, method=method, headers={"User-Agent": "codex-internet-check/1.0", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def percentile(values, p):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * p))]


def default_route():
    try:
        system = platform.system()
        if system == "Darwin":
            output = subprocess.run(["route", "-n", "get", "default"], capture_output=True, text=True, timeout=2, check=True).stdout
            result = {}
            for line in output.splitlines():
                key, _, value = line.strip().partition(":")
                if key in {"gateway", "interface"}:
                    result[key] = value.strip()
            return result
        if system == "Linux":
            output = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True, timeout=2, check=True).stdout
            fields = output.split()
            result = {}
            if "via" in fields:
                result["gateway"] = fields[fields.index("via") + 1]
            if "dev" in fields:
                result["interface"] = fields[fields.index("dev") + 1]
            return result
        if system == "Windows":
            output = subprocess.run(["route", "print", "-4"], capture_output=True, text=True, timeout=2, check=True).stdout
            for line in output.splitlines():
                fields = line.split()
                if len(fields) >= 3 and fields[0] == "0.0.0.0" and fields[1] == "0.0.0.0":
                    return {"gateway": fields[2], "interface": fields[3] if len(fields) > 3 else None}
        return {}
    except (OSError, subprocess.SubprocessError):
        return {}


def human_summary(result):
    timing = result["http_response_ms"]
    loaded = result["loaded_http_response_ms"]
    endpoint = urlsplit(result["endpoint"]).hostname or result["endpoint"]
    stamp = datetime.fromisoformat(result["timestamp_utc"]).astimezone().strftime("%Y-%m-%d %H:%M %Z")
    route = result["network_path"]
    route_parts = [route.get("interface"), f"gateway {route['gateway']}" if route.get("gateway") else None]
    route_text = " · ".join(part for part in route_parts if part) or "unavailable"
    simultaneous = result["simultaneous_load"]

    def value(number, unit, precision=2):
        return "Unavailable" if number is None else f"{number:.{precision}f} {unit}"

    if timing:
        idle_text = f"{value(timing.get('median'), 'ms')} median / {value(timing.get('p95'), 'ms')} p95"
        idle_failures = f"{timing.get('failed_probes_percent', 100):.1f}% failed"
    else:
        idle_text = idle_failures = "Unavailable"
    if loaded:
        loaded_text = f"{value(loaded.get('median'), 'ms')} median / {value(loaded.get('p95'), 'ms')} p95"
        delta = loaded.get("median") - timing.get("median") if timing and loaded.get("median") is not None and timing.get("median") is not None else None
        loaded_delta = "unavailable" if delta is None else f"{delta:+.2f} ms median change"
        loaded_failures = f"{loaded.get('failed_probes_percent', 100):.1f}% failed"
    else:
        loaded_text = loaded_delta = loaded_failures = "Unavailable"

    lines = [
        f"Internet speed test · {endpoint}",
        "─" * 48,
        f"Capacity    Download {value(result['download_mbps'], 'Mbps')} / Upload {value(result['upload_mbps'], 'Mbps')} · measured separately",
        f"Both active Download {value(simultaneous['download_mbps'], 'Mbps')} / Upload {value(simultaneous['upload_mbps'], 'Mbps')}",
        f"HTTP idle   {idle_text} · {idle_failures}",
        f"HTTP loaded {loaded_text} · {loaded_delta} · {loaded_failures}",
        f"Test        {result['flows']} flows per active direction · {result['duration_seconds']:.2f} s total",
        f"Route       {route_text}",
        f"Time        {stamp}",
        "Capacity and simultaneous-load rates describe different workloads.",
    ]
    if result["errors"]:
        lines.append(f"Warnings    {len(result['errors'])} issue(s); use --json for details")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default=os.environ.get("SPEEDTEST_ENDPOINT", "https://speedtest.codimeo.com/"))
    parser.add_argument("--pings", "--probes", dest="pings", type=int, default=6, choices=range(3, 31), help="number of idle HTTP response probes")
    parser.add_argument("--download-mib", type=int, default=25, choices=(5, 10, 25, 50), help="total download MiB per phase; transferred once for capacity and once for simultaneous load")
    parser.add_argument("--upload-mib", type=int, default=10, choices=(1, 5, 10, 25), help="total upload MiB per phase; transferred once for capacity and once for simultaneous load")
    parser.add_argument("--flows", type=int, default=3, choices=range(1, 5), help="parallel upload and download flows")
    parser.add_argument("--json", action="store_true", help="print the full machine-readable result")
    args = parser.parse_args()
    base = args.endpoint.rstrip("/")
    result = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "endpoint": base, "platform": platform.platform(), "network_path": default_route(), "http_response_ms": {}, "loaded_http_response_ms": {}, "download_mbps": None, "upload_mbps": None, "throughput_mode": "sequential_capacity", "capacity_phase_seconds": {}, "simultaneous_load": {"download_mbps": None, "upload_mbps": None, "duration_seconds": 0.0}, "flows": args.flows, "duration_seconds": 0.0, "errors": []}
    test_start = time.perf_counter()

    def probe(samples, errors):
        start = time.perf_counter()
        try:
            request(base + "/ping", timeout=10)
            samples.append((time.perf_counter() - start) * 1000)
        except Exception as exc:
            errors.append(f"HTTP probe: {exc}")

    def summarize(samples, requested):
        if not samples:
            return {}
        diffs = [abs(b - a) for a, b in zip(samples, samples[1:])]
        return {"min": round(min(samples), 2), "median": round(statistics.median(samples), 2), "p95": round(percentile(samples, .95), 2), "mean_abs_delta": round(statistics.mean(diffs), 2) if diffs else 0, "failed_probes_percent": round(100 * (requested - len(samples)) / requested, 1), "samples": len(samples)}

    idle_samples = []
    idle_errors = []
    for _ in range(args.pings):
        probe(idle_samples, idle_errors)
    result["http_response_ms"] = summarize(idle_samples, args.pings)
    result["errors"].extend(idle_errors)

    def transfer(direction, size):
        if direction == "download":
            payload = request(f"{base}/download?bytes={size}", timeout=90)
            if len(payload) != size:
                raise ValueError(f"expected {size} download bytes, received {len(payload)}")
        else:
            response = request(base + "/upload", "POST", b"0" * size, timeout=90)
            if response.strip() != f"ok {size}".encode():
                raise ValueError("server did not confirm upload")
        return direction, size, time.perf_counter()

    loaded_samples = []
    loaded_errors = []
    def split_size(total_mib):
        total = total_mib * 1024 * 1024
        quotient, remainder = divmod(total, args.flows)
        return [quotient + (index < remainder) for index in range(args.flows)]

    sizes = {"download": split_size(args.download_mib), "upload": split_size(args.upload_mib)}

    def run_phase(directions, label, probe_under_load=False):
        jobs = [(direction, size) for direction in directions for size in sizes[direction]]
        phase_start = time.perf_counter()
        loaded_requested = 0
        totals = {direction: [0, 0.0, 0] for direction in directions}
        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            futures = {pool.submit(transfer, direction, size): direction for direction, size in jobs}
            if probe_under_load:
                while any(not future.done() for future in futures) and loaded_requested < min(args.pings, 12):
                    probe(loaded_samples, loaded_errors)
                    loaded_requested += 1
                    if any(not future.done() for future in futures) and loaded_requested < min(args.pings, 12):
                        time.sleep(0.75)
            for future in as_completed(futures):
                try:
                    direction, size, finished = future.result()
                    totals[direction][0] += size
                    totals[direction][1] = max(totals[direction][1], finished - phase_start)
                    totals[direction][2] += 1
                except Exception as exc:
                    result["errors"].append(f"{label} {futures[future]} transfer: {exc}")
        rates = {}
        for direction, (byte_count, elapsed, completed) in totals.items():
            rates[direction + "_mbps"] = round(byte_count * 8 / elapsed / 1_000_000, 2) if completed == args.flows and elapsed else None
        return rates, round(time.perf_counter() - phase_start, 2), loaded_requested

    # Capacity phases must complete separately before the simultaneous-load phase.
    for direction in ("download", "upload"):
        rates, duration, _ = run_phase((direction,), "capacity")
        result.update(rates)
        result["capacity_phase_seconds"][direction] = duration

    rates, duration, loaded_requested = run_phase(("download", "upload"), "simultaneous load", probe_under_load=True)
    result["simultaneous_load"].update(rates, duration_seconds=duration)
    result["duration_seconds"] = round(time.perf_counter() - test_start, 2)
    result["loaded_http_response_ms"] = summarize(loaded_samples, loaded_requested)
    result["errors"].extend(loaded_errors)

    print(json.dumps(result, indent=2) if args.json else human_summary(result))
    if result["download_mbps"] is None and result["upload_mbps"] is None and not idle_samples and not loaded_samples:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
