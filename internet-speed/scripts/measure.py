#!/usr/bin/env python3
"""Stream separate-direction capacity, then HTTP responsiveness under simultaneous load."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import http.client
import json
import math
import os
import platform
import socket
import statistics
import subprocess
import threading
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit

SIZE_MB_OPTIONS = (70, 300, 1000)
CHUNK_SIZE = 64 * 1024
TRANSFER_TIMEOUT = 1800


def request(url, method="GET", data=None, timeout=10, headers=None):
    """Read only small acknowledgements, never transfer payloads."""
    req = urllib.request.Request(url, data=data, method=method, headers={"User-Agent": "chain-it-speedtest/2.0", "Cache-Control": "no-cache", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = response.read(4097)
        if len(body) > 4096:
            raise ValueError("Oversized acknowledgement")
        return body


class UploadBody:
    """One reusable buffer; no full-size allocation and no temporary file."""
    def __init__(self, size, progress=None):
        self.size = size
        self.progress = progress

    def __iter__(self):
        block = bytes(min(CHUNK_SIZE, self.size))
        sent = 0
        start = time.perf_counter()
        while sent < self.size:
            if time.perf_counter() - start > TRANSFER_TIMEOUT:
                raise TimeoutError("Upload exceeded the transfer time limit")
            count = min(len(block), self.size - sent)
            yield block if count == len(block) else block[:count]
            sent += count
            if self.progress:
                self.progress(sent)


def download_bytes(url, expected, progress=None):
    req = urllib.request.Request(url, headers={"User-Agent": "chain-it-speedtest/2.0", "Cache-Control": "no-cache"})
    start = time.perf_counter()
    received = 0
    with urllib.request.urlopen(req, timeout=TRANSFER_TIMEOUT) as response:
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            received += len(chunk)
            if received > expected:
                raise ValueError("Oversized download")
            if time.perf_counter() - start > TRANSFER_TIMEOUT:
                raise TimeoutError("Download exceeded the transfer time limit")
            if progress:
                progress(received)
            # This chunk is discarded on the next iteration, not stored or written.
    if received != expected:
        raise ValueError(f"expected {expected} download bytes, received {received}")
    return received


class ProgressTracker:
    def __init__(self, flows, started):
        self.lock = threading.Lock()
        self.observed = [0] * flows
        self.started = self.last_time = started
        self.last_bytes = 0
        self.samples = []

    def _sample(self, current):
        elapsed = current - self.last_time
        if elapsed <= 0:
            return
        total = sum(self.observed)
        self.samples.append({"seconds": current - self.started, "mbps": round((total - self.last_bytes) * 8 / elapsed / 1_000_000, 2), "bytes": total})
        self.last_time = current
        self.last_bytes = total

    def update(self, index, count):
        with self.lock:
            self.observed[index] = max(self.observed[index], count)
            current = time.perf_counter()
            if current - self.last_time >= 0.5:
                self._sample(current)

    def finish(self, current):
        with self.lock:
            self._sample(current)


def percentile(values, p):
    return sorted(values)[max(0, math.ceil(len(values) * p) - 1)] if values else None


def summarize(samples, requested):
    differences = [abs(b - a) for a, b in zip(samples, samples[1:])]
    return {
        "min": round(min(samples), 2) if samples else None,
        "median": round(statistics.median(samples), 2) if samples else None,
        "p95": round(percentile(samples, .95), 2) if samples else None,
        "mean_abs_delta": round(statistics.mean(differences), 2) if differences else None,
        "failed_probes_percent": round(100 * (requested - len(samples)) / requested, 2) if requested else None,
        "samples": len(samples), "requested": requested,
    }


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
                if len(fields) >= 4 and fields[:2] == ["0.0.0.0", "0.0.0.0"]:
                    return {"gateway": fields[2], "interface": fields[3]}
        return {}
    except (OSError, subprocess.SubprocessError):
        return {}


def human_summary(result):
    def value(number, unit, precision=2):
        return "Unavailable" if number is None else f"{number:.{precision}f} {unit}"
    idle, loaded = result["http_response_ms"], result["loaded_http_response_ms"]
    delta = loaded["median"] - idle["median"] if loaded["median"] is not None and idle["median"] is not None else None
    route = result["network_path"]
    route_text = " · ".join(part for part in [route.get("interface"), f"gateway {route['gateway']}" if route.get("gateway") else None] if part) or "unavailable"
    simultaneous = result["simultaneous_load"]
    lines = [
        f"Internet speed test · {urlsplit(result['endpoint']).hostname}",
        "─" * 48,
        f"Capacity    Download {value(result['download_mbps'], 'Mbps')} / Upload {value(result['upload_mbps'], 'Mbps')} · measured separately",
        f"Both active Download {value(simultaneous['download_mbps'], 'Mbps')} / Upload {value(simultaneous['upload_mbps'], 'Mbps')}",
        f"HTTP idle   {value(idle['median'], 'ms')} median / {value(idle['p95'], 'ms')} p95 · {value(idle['failed_probes_percent'], '%', 1)} failed",
        f"HTTP loaded {value(loaded['median'], 'ms')} median / {value(loaded['p95'], 'ms')} p95 · {value(loaded['failed_probes_percent'], '%', 1)} failed",
        f"HTTP change {value(delta, 'ms')} median change under load",
        f"Test        {result['flows']} flows per active direction · {result['duration_seconds']:.2f} s total · {result['payload_bytes'] / 1_000_000:g} MB payload budget",
        f"Route       {route_text}",
        f"Time        {datetime.fromisoformat(result['timestamp_utc']).astimezone().strftime('%Y-%m-%d %H:%M %Z')}",
        "Capacity and simultaneous-load rates describe different workloads.",
    ]
    if result["errors"]:
        lines.append(f"Warnings    {len(result['errors'])} issue(s); use --json for details")
    return "\n".join(lines)


def transfer_sizes(args, parser):
    legacy = args.download_mib is not None or args.upload_mib is not None
    if legacy:
        if args.size_mb is not None or args.download_mib is None or args.upload_mib is None:
            parser.error("provide both --download-mib and --upload-mib, without --size-mb")
        return None, args.download_mib * 1024 * 1024, args.upload_mib * 1024 * 1024
    size_mb = args.size_mb if args.size_mb is not None else 70
    return size_mb, size_mb * 1_000_000, size_mb * 1_000_000


def next_preset_fits(next_bytes, measured_bytes, elapsed, remaining):
    return all(math.isfinite(value) and value > 0 for value in (next_bytes, measured_bytes, elapsed, remaining)) and next_bytes * elapsed / measured_bytes <= remaining


class MeasurementLimit(Exception):
    pass


class TransferIntegrityError(ValueError):
    pass


class TransferWindow:
    """Stop only this measurement's sockets at one shared direction deadline."""
    def __init__(self, seconds=10):
        self.started = time.perf_counter()
        self.end = self.started + seconds
        self.seconds = seconds
        self.lock = threading.Lock()
        self.connections = set()
        self.sockets = {}
        self.active = {}
        self.stopped = threading.Event()
        self.timer = threading.Timer(seconds, self.expire)
        self.timer.daemon = True
        self.timer.start()

    def expired(self):
        return self.stopped.is_set() or time.perf_counter() >= self.end

    def elapsed(self):
        return min(self.seconds, max(0, time.perf_counter() - self.started))

    def register(self, connection):
        with self.lock:
            if self.expired():
                raise MeasurementLimit()
            self.connections.add(connection)

    def attach(self, connection):
        with self.lock:
            if self.expired():
                connection.close()
                raise MeasurementLimit()
            self.sockets[connection] = connection.sock

    def release(self, connection, direction):
        with self.lock:
            self.connections.discard(connection)
            self.sockets.pop(connection, None)
            self.active[direction] -= 1

    def both_active(self):
        with self.lock:
            return self.active.get('download', 0) > 0 and self.active.get('upload', 0) > 0

    def expire(self):
        self.stopped.set()
        with self.lock:
            connections = [(connection, self.sockets.get(connection) or connection.sock) for connection in self.connections]
        for connection, owned_socket in connections:
            try:
                if owned_socket:
                    owned_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()

    def close(self):
        self.timer.cancel()


def adaptive_transfer(base, direction, size, progress, window):
    address = urlsplit(base)
    connection_type = http.client.HTTPSConnection if address.scheme == 'https' else http.client.HTTPConnection
    connection = connection_type(address.hostname, address.port, timeout=max(.001, window.end - time.perf_counter()))
    upload_id = uuid.uuid4().hex if direction == 'upload' else None
    path = address.path.rstrip('/') + (f'/download?bytes={size}' if direction == 'download' else f'/upload?id={upload_id}')
    count = 0
    planned = False
    finished = 0
    registered = False
    try:
        window.register(connection)
        registered = True
        connection.connect()
        window.attach(connection)
        if window.expired():
            raise MeasurementLimit()
        headers = {'User-Agent': 'chain-it-speedtest/3.0', 'Cache-Control': 'no-cache'}
        if direction == 'download':
            connection.request('GET', path, headers=headers)
            response = connection.getresponse()
            if response.status != 200:
                raise TransferIntegrityError(f'HTTP {response.status}')
            while True:
                if window.expired():
                    raise MeasurementLimit()
                chunk = response.read1(CHUNK_SIZE)
                if window.expired():
                    raise MeasurementLimit()
                if not chunk:
                    break
                count += len(chunk)
                if count > size:
                    raise TransferIntegrityError('Oversized download')
                if progress:
                    progress(count)
            if count != size:
                raise TransferIntegrityError('Incomplete download')
        else:
            connection.putrequest('POST', path)
            for key, value in {**headers, 'Content-Type': 'application/octet-stream', 'Content-Length': str(size)}.items():
                connection.putheader(key, value)
            connection.endheaders()
            block = bytes(min(CHUNK_SIZE, size))
            while count < size:
                if window.expired():
                    raise MeasurementLimit()
                amount = min(len(block), size - count)
                connection.send(block if amount == len(block) else block[:amount])
                if window.expired():
                    raise MeasurementLimit()
                count += amount
                if progress:
                    progress(count)
            response = connection.getresponse()
            if response.status != 200:
                raise TransferIntegrityError(f'HTTP {response.status}')
            if response.read(4097).strip() != f'ok {size}'.encode():
                raise TransferIntegrityError('Invalid upload acknowledgement')
    except Exception as exc:
        if isinstance(exc, TransferIntegrityError) or not window.expired():
            raise
        planned = True
    finally:
        finished = window.elapsed()
        if registered:
            window.release(connection, direction)
        else:
            with window.lock:
                window.active[direction] -= 1
        connection.close()
    if planned and direction == 'upload':
        receipt = json.loads(request(base + '/upload-receipt/' + upload_id, timeout=5))
        received = receipt.get('received')
        if receipt.get('finalized') is not True or receipt.get('error') is not False or type(receipt.get('complete')) is not bool or type(received) is not int or not 0 <= received <= size or (receipt['complete'] and received != size):
            raise ValueError('Upload receipt unavailable or invalid')
        count = received
    return count, finished, planned


def run_adaptive(base, flows=3, probes=6, max_size_mb=1000, phase_seconds=10):
    if max_size_mb not in SIZE_MB_OPTIONS or not 0 < phase_seconds <= 10:
        raise ValueError('Invalid adaptive limits')
    capabilities = json.loads(request(base + '/capabilities'))
    if capabilities.get('adaptive_version') != 1:
        raise ValueError('This server does not support adaptive measurements')
    presets = [size for size in SIZE_MB_OPTIONS if size <= max_size_mb]
    result = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'endpoint': base,
        'platform': platform.platform(), 'network_path': default_route(), 'throughput_mode': 'sequential_capacity',
        'measurement_mode': 'adaptive_10s', 'size_mb': None, 'max_size_mb': max_size_mb, 'phase_limit_seconds': phase_seconds,
        'payload_bytes': 2 * sum(size * 1000000 for size in presets) + 140000000,
        'flows': flows, 'duration_seconds': 0, 'errors': [], 'download_mbps': None, 'upload_mbps': None,
        'capacity_phase_seconds': {}, 'capacity_samples': {'download': [], 'upload': []},
        'capacity_stages': {}, 'capacity_bytes': {}, 'capacity_stop_reason': {}, 'simultaneous_load': {},
        'http_response_ms': {}, 'loaded_http_response_ms': {},
        'sample_basis': {'download': 'received_bytes', 'upload': 'client_socket_write_progress'},
    }
    started = time.perf_counter()

    def probe(samples, label, window=None):
        before = time.perf_counter()
        try:
            remaining = max(.001, window.end - before) if window else 10
            if request(base + '/ping', timeout=min(10, remaining)).strip() != b'ok':
                raise ValueError('Invalid ping acknowledgement')
            if window and window.expired():
                return False
            samples.append((time.perf_counter() - before) * 1000)
        except Exception as exc:
            if window and window.expired():
                return False
            result['errors'].append(f'{label} HTTP probe: {exc}')
        return True

    idle = []
    for _ in range(probes):
        probe(idle, 'idle')
    result['http_response_ms'] = summarize(idle, probes)

    def stage(directions, size_mb, window, trackers=None):
        before = window.elapsed()
        totals = {direction: 0 for direction in directions}
        finished = {direction: before for direction in directions}
        failed = {direction: False for direction in directions}
        offsets = {direction: list(trackers[direction].observed) for direction in directions} if trackers else {}
        with window.lock:
            for direction in directions:
                window.active[direction] = flows
        with ThreadPoolExecutor(max_workers=flows * len(directions)) as pool:
            futures = {}
            for direction in directions:
                quotient, remainder = divmod(size_mb * 1000000, flows)
                for index in range(flows):
                    size = quotient + (index < remainder)
                    progress = (lambda count, d=direction, i=index: trackers[d].update(i, offsets[d][i] + count)) if trackers else None
                    futures[pool.submit(adaptive_transfer, base, direction, size, progress, window)] = direction
            loaded, requested = [], 0
            while len(directions) == 2 and window.both_active() and not window.expired() and requested < min(probes, 12):
                if not probe(loaded, 'simultaneous_load', window):
                    break
                requested += 1
                if window.both_active() and requested < min(probes, 12):
                    window.stopped.wait(min(.75, max(0, window.end - time.perf_counter())))
            for future in as_completed(futures):
                direction = futures[future]
                try:
                    count, elapsed, planned = future.result()
                    totals[direction] += count
                    finished[direction] = max(finished[direction], elapsed)
                except Exception as exc:
                    failed[direction] = True
                    finished[direction] = max(finished[direction], window.elapsed())
                    result['errors'].append(f'{"capacity" if trackers else "simultaneous_load"} {direction} transfer: {exc}')
        return totals, finished, failed, summarize(loaded, requested)

    for direction in ('download', 'upload'):
        window = TransferWindow(phase_seconds)
        tracker = ProgressTracker(flows, window.started)
        count = 0
        elapsed = 0
        failed = False
        reason = 'largest_preset_complete'
        stages = []
        try:
            for index, size in enumerate(presets):
                if window.expired():
                    reason = 'time_limit'
                    break
                before = elapsed
                totals, finished, errors, _ = stage((direction,), size, window, {direction: tracker})
                count += totals[direction]
                elapsed = finished[direction]
                failed = errors[direction]
                stages.append({'size_mb': size, 'bytes': totals[direction], 'seconds': round(max(0, elapsed - before), 2),
                               'stop_reason': 'error' if failed else 'time_limit' if window.expired() else 'size_complete'})
                if failed:
                    reason = 'error'
                    break
                if window.expired():
                    reason = 'time_limit'
                    break
                if index + 1 < len(presets) and not next_preset_fits(presets[index + 1] * 1000000, count, window.elapsed(), max(0, window.end - time.perf_counter())):
                    reason = 'next_preset_wont_fit'
                    break
            tracker.finish(window.started + elapsed)
        finally:
            window.close()
        result[direction + '_mbps'] = round(count * 8 / elapsed / 1000000, 2) if not failed and elapsed > 0 else None
        result['capacity_phase_seconds'][direction] = round(elapsed, 2)
        result['capacity_samples'][direction] = tracker.samples
        result['capacity_bytes'][direction] = count
        result['capacity_stages'][direction] = stages
        result['capacity_stop_reason'][direction] = reason
    window = TransferWindow(phase_seconds)
    try:
        totals, finished, failed, timing = stage(('download', 'upload'), 70, window)
    finally:
        window.close()
    result['simultaneous_load'] = {'duration_seconds': round(max(finished.values()), 2), 'bytes': totals}
    for direction in ('download', 'upload'):
        result['simultaneous_load'][direction + '_mbps'] = round(totals[direction] * 8 / finished[direction] / 1000000, 2) if not failed[direction] and finished[direction] > 0 else None
    result['loaded_http_response_ms'] = timing
    result['duration_seconds'] = round(time.perf_counter() - started, 2)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default=os.environ.get("SPEEDTEST_ENDPOINT", "https://speed-test.chain-it.com/"))
    parser.add_argument("--pings", "--probes", dest="pings", type=int, default=6, choices=range(3, 31), help="idle HTTP probes")
    parser.add_argument("--size-mb", type=int, choices=SIZE_MB_OPTIONS, help="explicit fixed-volume diagnostic mode; not adaptive")
    parser.add_argument("--max-size-mb", type=int, choices=SIZE_MB_OPTIONS, help="largest adaptive preset; default 1000; one 10-second window per direction")
    parser.add_argument("--download-mib", type=int, choices=(5, 10, 25, 50), help="legacy explicit download MiB per phase; requires --upload-mib")
    parser.add_argument("--upload-mib", type=int, choices=(1, 5, 10, 25), help="legacy explicit upload MiB per phase; requires --download-mib")
    parser.add_argument("--flows", type=int, default=3, choices=range(1, 5))
    parser.add_argument("--json", action="store_true", help="full result including capacity time-series samples")
    args = parser.parse_args()
    if args.max_size_mb is not None and any(value is not None for value in (args.size_mb, args.download_mib, args.upload_mib)):
        parser.error('--max-size-mb cannot be mixed with fixed-volume options')
    base = args.endpoint.rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        parser.error("endpoint must be an HTTP(S) base URL without credentials, query or fragment")
    if all(value is None for value in (args.size_mb, args.download_mib, args.upload_mib)):
        try:
            result = run_adaptive(base, args.flows, args.pings, args.max_size_mb or 1000)
        except Exception:
            parser.exit(1, 'Adaptive measurement could not start. Check connectivity and server protocol support.\n')
        print(json.dumps(result, indent=2) if args.json else human_summary(result))
        if result['download_mbps'] is None and result['upload_mbps'] is None:
            raise SystemExit(1)
        return
    size_mb, download_size, upload_size = transfer_sizes(args, parser)
    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(), "endpoint": base,
        "platform": platform.platform(), "network_path": default_route(),
        "http_response_ms": {}, "loaded_http_response_ms": {}, "download_mbps": None, "upload_mbps": None,
        "throughput_mode": "sequential_capacity", "capacity_phase_seconds": {},
        "capacity_samples": {"download": [], "upload": []},
        "sample_basis": {"download": "received_bytes", "upload": "client_socket_write_progress"},
        "simultaneous_load": {"download_mbps": None, "upload_mbps": None, "duration_seconds": 0.0},
        "size_mb": size_mb, "payload_bytes": 2 * (download_size + upload_size),
        "flows": args.flows, "duration_seconds": 0.0, "errors": [],
    }
    test_start = time.perf_counter()

    def probe(samples, label):
        start = time.perf_counter()
        try:
            if request(base + "/ping").strip() != b"ok":
                raise ValueError("Invalid ping acknowledgement")
            samples.append((time.perf_counter() - start) * 1000)
        except Exception as exc:
            result["errors"].append(f"{label} HTTP probe: {exc}")

    idle = []
    for _ in range(args.pings):
        probe(idle, "idle")
    result["http_response_ms"] = summarize(idle, args.pings)

    def split(total):
        quotient, remainder = divmod(total, args.flows)
        return [quotient + (index < remainder) for index in range(args.flows)]
    sizes = {"download": split(download_size), "upload": split(upload_size)}

    def transfer(direction, size, progress):
        if direction == "download":
            download_bytes(f"{base}/download?bytes={size}", size, progress)
        else:
            response = request(base + "/upload", "POST", UploadBody(size, progress), timeout=TRANSFER_TIMEOUT,
                               headers={"Content-Type": "application/octet-stream", "Content-Length": str(size)})
            if response.strip() != f"ok {size}".encode():
                raise ValueError("server did not confirm upload")
        return size, time.perf_counter()

    def run_phase(directions, label, under_load=False):
        started = time.perf_counter()
        totals = {direction: [0, 0.0, 0] for direction in directions}
        trackers = {direction: ProgressTracker(args.flows, started) for direction in directions} if not under_load else {}
        loaded, requested = [], 0
        with ThreadPoolExecutor(max_workers=args.flows * len(directions)) as pool:
            futures = {}
            for direction in directions:
                for index, size in enumerate(sizes[direction]):
                    progress = (lambda count, d=direction, i=index: trackers[d].update(i, count)) if direction in trackers else None
                    futures[pool.submit(transfer, direction, size, progress)] = direction
            def both_active():
                return all(any(not future.done() and direction == wanted for future, direction in futures.items()) for wanted in ("download", "upload"))
            while under_load and both_active() and requested < min(args.pings, 12):
                requested += 1
                probe(loaded, label)
                if both_active() and requested < min(args.pings, 12):
                    time.sleep(.75)
            for future in as_completed(futures):
                direction = futures[future]
                try:
                    count, finished = future.result()
                    totals[direction][0] += count
                    totals[direction][1] = max(totals[direction][1], finished - started)
                    totals[direction][2] += 1
                except Exception as exc:
                    result["errors"].append(f"{label} {direction} transfer: {exc}")
        rates = {}
        for direction, (count, elapsed, completed) in totals.items():
            rates[direction + "_mbps"] = round(count * 8 / elapsed / 1_000_000, 2) if completed == args.flows and elapsed > 0 else None
            if direction in trackers:
                trackers[direction].finish(started + elapsed if completed == args.flows else time.perf_counter())
                result["capacity_samples"][direction] = trackers[direction].samples
        return rates, round(time.perf_counter() - started, 2), summarize(loaded, requested)

    for direction in ("download", "upload"):
        rates, duration, _ = run_phase((direction,), direction)
        result.update(rates)
        result["capacity_phase_seconds"][direction] = duration
    rates, duration, timing = run_phase(("download", "upload"), "simultaneous_load", under_load=True)
    result["simultaneous_load"].update(rates, duration_seconds=duration)
    result["loaded_http_response_ms"] = timing
    result["duration_seconds"] = round(time.perf_counter() - test_start, 2)
    print(json.dumps(result, indent=2) if args.json else human_summary(result))
    if result["download_mbps"] is None and result["upload_mbps"] is None and not idle and not timing["samples"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
