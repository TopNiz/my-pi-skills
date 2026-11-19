#!/usr/bin/env python3
"""FastAPI service for bounded Internet download and upload measurements."""

import asyncio
import os
import re
from time import monotonic
from collections.abc import Iterator
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from starlette.requests import ClientDisconnect

# Decimal bytes: each direction supports the 70 MB, 300 MB and 1 GB presets.
MAX_DOWNLOAD = 1_000_000_000
MAX_UPLOAD = 1_000_000_000
CHUNK_SIZE = 64 * 1024
RECEIPT_TTL = 30
MAX_RECEIPTS = 1024
# Only bounded, short-lived byte counters. No payloads, client addresses or history.
UPLOAD_RECEIPTS: dict[str, dict] = {}

def configured_origins(value: str) -> set[str]:
    origins = set()
    for item in value.split(','):
        item = item.strip().rstrip('/')
        if not item:
            continue
        parsed = urlsplit(item)
        if any(character.isspace() for character in item) or parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
            raise ValueError('Invalid allowed UI origin')
        parsed.port  # Validate the port without logging configuration values.
        origins.add(item)
    return origins


ALLOWED_UI_ORIGINS = configured_origins(os.environ.get('SPEEDTEST_ALLOWED_ORIGINS', ''))
PUBLIC_API_ORIGIN = 'https://speed-test.chain-it.com'
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CORSMiddleware, allow_origins=sorted(ALLOWED_UI_ORIGINS), allow_credentials=False,
                   allow_methods=['GET', 'POST', 'OPTIONS'], allow_headers=['Content-Type', 'Cache-Control'], max_age=300)


@app.middleware("http")
async def no_store_responses(request: Request, call_next):
    measurement_path = request.url.path in {"/ping", "/download", "/upload", "/capabilities"} or request.url.path.startswith("/upload-receipt/")
    origin = request.headers.get('origin')
    trusted_origin = origin in ALLOWED_UI_ORIGINS or origin == PUBLIC_API_ORIGIN
    if measurement_path and ((origin is not None and not trusted_origin) or (request.headers.get('sec-fetch-site') == 'cross-site' and not trusted_origin)):
        response = PlainTextResponse("Cross-site measurements are not allowed", status_code=403)
    else:
        response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0, no-transform"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
        "img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    )
    if request.url.path in {"/ping", "/download", "/upload"}:
        response.headers["X-Accel-Buffering"] = "no"
    return response


@app.get("/")
async def index():
    return {"service": "Chain-IT speed-test API", "role": "api", "adaptive_version": 1}


@app.get("/ping", response_class=PlainTextResponse)
async def ping() -> str:
    return "ok\n"


@app.get("/capabilities")
async def capabilities():
    return {"adaptive_version": 1, "phase_seconds": 10, "presets_mb": [70, 300, 1000], "load_bytes": 70_000_000, "max_request_bytes": MAX_DOWNLOAD}


def reserve_receipt(identifier: str):
    if not re.fullmatch(r"[a-f0-9]{32}", identifier):
        raise HTTPException(status_code=400, detail="invalid upload receipt identifier")
    if identifier in UPLOAD_RECEIPTS:
        raise HTTPException(status_code=409, detail="upload receipt already exists")
    if len(UPLOAD_RECEIPTS) >= MAX_RECEIPTS:
        raise HTTPException(status_code=503, detail="upload receipts temporarily unavailable")
    record = {"received": 0, "finalized": False, "complete": False, "error": False}
    UPLOAD_RECEIPTS[identifier] = record
    def expire():
        if UPLOAD_RECEIPTS.get(identifier) is record:
            UPLOAD_RECEIPTS.pop(identifier, None)
    asyncio.get_running_loop().call_later(RECEIPT_TTL, expire)
    return record


@app.get("/upload-receipt/{upload_id}")
async def upload_receipt(upload_id: str):
    if not re.fullmatch(r"[a-f0-9]{32}", upload_id):
        raise HTTPException(status_code=400, detail="invalid upload receipt identifier")
    record = UPLOAD_RECEIPTS.get(upload_id)
    if record is None:
        raise HTTPException(status_code=404, detail="upload receipt unavailable")
    deadline = monotonic() + 2
    while not record["finalized"] and monotonic() < deadline:
        await asyncio.sleep(.02)
    return dict(record)


@app.get("/download")
async def download(request: Request) -> StreamingResponse:
    try:
        size = int(request.query_params.get("bytes", ""))
    except ValueError:
        size = 0
    if not 1 <= size <= MAX_DOWNLOAD:
        raise HTTPException(status_code=400, detail="bytes must be between 1 and 1000000000")

    def random_chunks() -> Iterator[bytes]:
        remaining = size
        while remaining:
            chunk_size = min(CHUNK_SIZE, remaining)
            yield os.urandom(chunk_size)
            remaining -= chunk_size

    return StreamingResponse(
        random_chunks(),
        media_type="application/octet-stream",
        headers={"Content-Length": str(size)},
    )


@app.post("/upload", response_class=PlainTextResponse)
async def upload(request: Request) -> str:
    try:
        declared_size = int(request.headers.get("content-length", "0"))
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid Content-Length")
    if not 1 <= declared_size <= MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="upload must be between 1 and 1000000000 bytes")

    identifier = getattr(request, "query_params", {}).get("id")
    record = reserve_receipt(identifier) if identifier is not None else None
    received = 0
    try:
        # Tagged adaptive uploads must end promptly even if the client disappears.
        async with asyncio.timeout(12 if record is not None else 1800):
            async for chunk in request.stream():
                received += len(chunk)
                if received > declared_size:
                    raise HTTPException(status_code=400, detail="upload exceeds declared bytes")
                if record is not None:
                    record["received"] = received
        if received != declared_size:
            raise HTTPException(status_code=400, detail="incomplete upload")
        if record is not None:
            record["complete"] = True
        return f"ok {received}\n"
    except ClientDisconnect:
        # The client can verify these exact received bytes after its planned cutoff.
        if record is None:
            raise
        return f"partial {received}\n"
    except BaseException:
        if record is not None:
            record["error"] = True
        raise
    finally:
        if record is not None:
            record["finalized"] = True


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), access_log=False)
