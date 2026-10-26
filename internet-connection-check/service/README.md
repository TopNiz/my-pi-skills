# Codimeo speed-test service

Standalone FastAPI service for `https://speedtest.codimeo.com/`, served by Uvicorn. It provides `/ping`, `/download?bytes=N` and `/upload`. Download is capped at 50 MiB and upload at 25 MiB. The client defaults to 25 MiB down and 10 MiB up per phase: 70 MiB total across capacity and simultaneous load. The service does not persist data or log client addresses.

Capacity is always measured with download-only flows followed by upload-only flows. A separate simultaneous download/upload phase measures HTTP responsiveness under load and reports its throughput independently. Never use simultaneous-load throughput as the capacity result. Run the installed client with `python3 ../scripts/measure.py --json` from this service folder.

The deployment target is `rg.fr-par.scw.cloud/chain-it/internet-speedtest` on `codimeo.com`. [The GitHub Actions workflow](.github/workflows/publish-image.yml) builds and smoke-tests this image, pushes immutable and moving tags, then uses a dedicated SSH deploy key to update a standalone Compose project on the host. It expects repository secrets `SCW_ACCESS_KEY`, `SCW_SECRET_KEY`, `CODIMEO_DEPLOY_SSH_KEY` and `CODIMEO_KNOWN_HOSTS`. The container binds to `127.0.0.1:18010` behind Nginx TLS.

The endpoint is live at `https://speedtest.codimeo.com/`. The app is intentionally unauthenticated; Nginx applies rate and body-size limits, and the container port is not exposed publicly. See `deployment.md` for host configuration and recovery details.
