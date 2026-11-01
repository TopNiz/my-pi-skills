#!/usr/bin/env python3
"""FastAPI service for bounded Internet download and upload measurements."""

import os
from collections.abc import Iterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse

MAX_DOWNLOAD = 50 * 1024 * 1024
MAX_UPLOAD = 25 * 1024 * 1024
CHUNK_SIZE = 64 * 1024

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Cache-Control"],
)


@app.middleware("http")
async def no_store_responses(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/", response_class=PlainTextResponse)
@app.get("/ping", response_class=PlainTextResponse)
async def ping() -> str:
    return "ok\n"


@app.get("/download")
async def download(request: Request) -> StreamingResponse:
    try:
        size = int(request.query_params.get("bytes", ""))
    except ValueError:
        size = 0
    if not 1 <= size <= MAX_DOWNLOAD:
        raise HTTPException(status_code=400, detail="bytes must be between 1 and 52428800")

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
        raise HTTPException(status_code=413, detail="upload must be between 1 and 26214400 bytes")

    received = 0
    async for chunk in request.stream():
        received += len(chunk)
        if received > MAX_UPLOAD:
            raise HTTPException(status_code=413, detail="upload must be at most 26214400 bytes")
    if received != declared_size:
        raise HTTPException(status_code=400, detail="incomplete upload")
    return f"ok {received}\n"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), access_log=False)
