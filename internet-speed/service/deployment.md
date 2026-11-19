# Production deployment on Codimeo

The FastAPI application is served by Uvicorn inside the image on port `8080`; the host Compose file binds it to `127.0.0.1:18010`. Host Nginx terminates TLS and reverse-proxies to that loopback address. The image contains no PHP runtime or PHP-FPM.

## GitHub Actions and registry

Publish this directory as the root of a private GitHub repository (the workflow is under `.github/workflows/`). Add repository secrets:

- `SCW_ACCESS_KEY` and `SCW_SECRET_KEY`: push-only Scaleway IAM credentials for namespace `chain-it`.
- `CODIMEO_DEPLOY_SSH_KEY` and `CODIMEO_KNOWN_HOSTS`: the dedicated deployment identity and pinned host key for `codimeo.com`.

Pushes to `main` and pull requests build and smoke-test the image. A manual `workflow_dispatch` on `main` publishes `:prod` and `:sha-<commit>` and deploys the `:prod` image over SSH. This manual gate prevents unreviewed image publication or restart. The server requires a working read-only login to `rg.fr-par.scw.cloud`.

## Codimeo host configuration

DNS for the single UI/API hostname `speed-test.chain-it.com` points to Codimeo, and Certbot provisions its HTTPS certificate. Nginx terminates TLS and proxies to `127.0.0.1:18010`; the container is not exposed directly to the Internet.

Nginx loads the per-IP request zone from `/etc/nginx/conf.d/speedtest-rate-limit.conf`:

```nginx
limit_req_zone $binary_remote_addr zone=speedtest:10m rate=30r/m;
```

The production deployment and TLS Nginx configuration are maintained in `TopNiz/internet-speedtest`. Preserve the approved public UI at `/` and `/static/` during API updates. New UI work remains local and uses an explicit remote API URL; publishing or removing the public UI requires explicit user approval. Configure `SPEEDTEST_ALLOWED_ORIGINS=http://127.0.0.1:63035,http://localhost:63035` for the approved local preview; other origins are denied, and CORS credentials are disabled. Use that repository's deployment instructions for the shared UI/API service. The former Codimeo speed-test hostname is retired, not a second API alias. The bundled configuration is an HTTP-only API bootstrap template for self-hosting; add TLS before public use.

The Nginx site limits requests to 30/minute with a burst of 120 including cross-origin preflights and disables compression and proxy buffering. Its request-body allowance is `1000m` (binary units); the API enforces exactly 1,000,000,000 bytes per direction per request. Client-body and upstream idle timeouts are 1800 seconds. Obtain approval to install only the speed-test-specific Nginx configuration, test it with `nginx -t`, and reload Nginx before exposing larger presets. Preserve other sites, TLS and the shared rate-limit zone. The repository's normal container workflow does not update host Nginx.

Each direction starts at 70 MB, then adds a full 300 MB and 1 GB only when the next stage's predicted duration fits one shared 10-second direction budget. A planned cutoff is normal; uploads require server-confirmed partial-byte receipts. The separate simultaneous-load phase uses up to 70 MB per direction in its own shared 10-second window. Escalation ceilings of 70 MB, 300 MB and 1 GB bound total payload at 280 MB, 880 MB and 2.88 GB respectively. Receipt checks can add a short wait after transfer windows close. Data is streamed and discarded without writing files. Counters expire from server memory after 30 seconds and are bounded at 1024. Use one Uvicorn worker, or provide affinity/shared counters if scaling. Deploy the API and client together and verify capability protocol 1 before transferring. The workflow waits for `/ping` before reporting success. Use small compatibility sizes for automated smoke tests; ask before full 1 GB acceptance transfers. Monitor server egress and container health.
