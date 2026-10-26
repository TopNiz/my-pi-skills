# Production deployment on Codimeo

The FastAPI application is served by Uvicorn inside the image on port `8080`; the host Compose file binds it to `127.0.0.1:18010`. Host Nginx terminates TLS and reverse-proxies to that loopback address. The image contains no PHP runtime or PHP-FPM.

## GitHub Actions and registry

Publish this directory as the root of a private GitHub repository (the workflow is under `.github/workflows/`). Add repository secrets:

- `SCW_ACCESS_KEY` and `SCW_SECRET_KEY`: push-only Scaleway IAM credentials for namespace `chain-it`.
- `CODIMEO_DEPLOY_SSH_KEY` and `CODIMEO_KNOWN_HOSTS`: the dedicated deployment identity and pinned host key for `codimeo.com`.

Pushes to `main` and pull requests build and smoke-test the image. A manual `workflow_dispatch` on `main` publishes `:prod` and `:sha-<commit>` and deploys the `:prod` image over SSH. This manual gate prevents unreviewed image publication or restart. The server requires a working read-only login to `rg.fr-par.scw.cloud`.

## Codimeo host configuration

DNS for `speedtest.codimeo.com` points to Codimeo, and Certbot provisions its HTTPS certificate. Nginx terminates TLS and proxies to `127.0.0.1:18010`; the container is not exposed directly to the Internet.

Nginx loads the per-IP request zone from `/etc/nginx/conf.d/speedtest-rate-limit.conf`:

```nginx
limit_req_zone $binary_remote_addr zone=speedtest:10m rate=30r/m;
```

The Nginx site limits requests to 30/minute with a burst of 30, disables proxy buffering, and caps request bodies at 26 MiB. The repository's workflow recreates the container from the published image and waits for `/ping` before reporting success. A default full client measurement transfers 70 MiB (35 MiB for separate-direction capacity, then 35 MiB for simultaneous load); monitor server egress and container health accordingly.
