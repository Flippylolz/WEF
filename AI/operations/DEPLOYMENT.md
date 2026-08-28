# Deployment

## Delivery model

The MVP runs as a Docker Compose project on one Linux server. GitHub-hosted runners build application images; the production host pulls immutable images and never builds source code.

All project-owned application processes are containerized. External providers—GitHub, OpenFreeMap, the selected geocoder, Telegram, and DNS—remain managed dependencies.

## Environments

The project has only local development and production. There is no persistent staging environment. Pull-request validation uses ephemeral CI containers/fixtures, and the first production deployment is rehearsed with synthetic/empty data before importing the historical dataset.

### Local development

Required host software:

- Docker Engine/Desktop with Compose v2.
- Git.

Node, Python, PostgreSQL, Caddy, Nginx, and Certbot do not need to be installed directly on the host; approved runtime components remain containerized.

Local Compose services:

- `web`: Next.js development or production-like mode.
- `api`: FastAPI with reload only in the development override.
- `db`: a pinned PostGIS image with a named volume.
- `caddy`: optional local same-origin routing.
- `importer`: same backend image, run as an on-demand command.
- `telegram-worker`: optional local listener. Enable with `docker compose --profile telegram-worker` after `WEF_TELEGRAM_API_ID` and `WEF_TELEGRAM_API_HASH` are set in the gitignored repo-root `.env`. The worker generates a Telethon string session on first login (`WEF_TELEGRAM_PHONE`, then `WEF_TELEGRAM_LOGIN_CODE` if not a TTY) and persists it to `WEF_TELEGRAM_SESSION` / `secrets/telegram/session`. Compose healthchecks both the backward-compatible transport timestamp and the versioned critical-loop runtime-health document via `wef-telegram-worker-status --liveness` (never gates `/api/v1/health/ready`). Observe checkpoint freshness with `wef-telegram-worker-status`. Rehearse rotation with `wef-telegram-worker-status --rotation-dry-run`.

The raw export is mounted read-only only into importer commands. Media output uses a named/local volume. The repository root is the Docker build context only with a strict `.dockerignore` excluding the export, archives, media, secrets, caches, and local database files.

Expected operator flows:

```text
make up
WEF_SOURCE_DIR=/absolute/path/to/export make import-dry-run
WEF_SOURCE_DIR=/absolute/path/to/export make import-run
make test
```

The import stages are resumable and no workflow may copy the full export into an image layer.

### Production

Production services:

- `caddy`: configurable `WEF_PUBLIC_PORT`, currently `3100/TCP`, retained as an application-owned rollback/diagnostic listener that cannot support production Secure-cookie flows.
- `nginx` plus `certbot`: the live standard 80/443 ingress with automatically renewed TLS for WEF on `2fa54e2405.duckdns.org`. AI Forecast stays on public host port `3000`. [E7-T8](../epics/E7-production-delivery/tasks/E7-T8-build-shared-nginx-tls-ingress.md), [E7-T9](../epics/E7-production-delivery/tasks/E7-T9-implement-reversible-shared-edge-cutover.md), and [E7-T10](../epics/E7-production-delivery/tasks/E7-T10-roll-out-and-verify-shared-tls.md) delivered and proved this dedicated `wef-shared-edge` Compose project. Ordinary `wef-production` releases reconnect their upstreams but neither deploy nor remove the shared edge.
- `web`: internal port only.
- `api`: internal port only.
- `db`: an application-owned PostgreSQL/PostGIS container on the internal network only, with a persistent host-backed volume.
- `telegram-worker`: one replica. Host env comes from the deploy-managed `production.env` (`WEF_TELEGRAM_API_ID`, `WEF_TELEGRAM_API_HASH`, optional `WEF_TELEGRAM_SESSION` / `WEF_TELEGRAM_PHONE`). Generated sessions persist under `${WEF_ROOT}/secrets/telegram/` (mode 0700). Ordinary production deploys start the worker after API/web/edge; the container healthcheck requires fresh transport and serialized-consumer state from the runtime-health document and never gates public readiness. E15-T1 leaves reconciliation explicitly `pending_implementation`; E15-T2 makes that real loop mandatory.

The importer is a run-to-completion command, not an always-running service. The production Compose project is explicitly named `wef-production`; it does not reuse an existing container, network, volume, database, or Compose project.

## Image strategy

Build two application images:

- `ghcr.io/<owner>/<repository>-web:<git-sha>`.
- `ghcr.io/<owner>/<repository>-backend:<git-sha>`.

The backend image supplies API, migration, importer, verification, and Telegram-listener commands. Each service chooses a different entry command.

Image requirements:

- Multi-stage builds with dependencies locked.
- Minimal maintained runtime bases pinned by digest through controlled dependency updates.
- OCI source/revision labels.
- Non-root application user.
- No development dependencies in final images where avoidable.
- No source export, generated media, `.env`, tests containing sensitive samples, OpenAPI contracts/static docs/documentation generators, or build credentials.
- BuildKit cache for speed, never for secret persistence.
- A release is identified by the full Git commit SHA, not only `latest`.

`latest` may be published for convenience but production Compose always resolves an explicit SHA.

## Compose layout

- `infra/compose.yaml`: shared service definitions usable locally.
- `infra/compose.production.yaml`: production images, restart policy, resources, networks, volumes, and hardened settings.
- `infra/Caddyfile.production`: application-owned rollback same-origin routes.
- `infra/compose.shared-edge.yaml`: the separately managed `wef-shared-edge` project (Nginx plus Certbot) with a fixed-name `wef-edge` network owned by the edge boundary. `infra/compose.shared-edge-fixtures.yaml` is a proof-only override (fixture upstreams and local Pebble ACME) that must never be combined with a production edge deployment.
- `infra/nginx/` owns the HTTP-only ACME bootstrap template (`bootstrap.conf.in`), the TLS templates (`tls.conf.in`, `tls-redirect.conf.in`), the optional Forecast vhost fragment (`forecast-vhost.conf.in`), and the Certbot deploy hook (`deploy-hook.sh`). `scripts/deploy/shared_edge_render.py` renders deterministic validated releases (WEF-only when Forecast hostname/upstream are omitted; dual-host when both are set), `scripts/deploy/shared_edge_release.py` validates (`nginx -t` as the serving UID) and atomically activates/rolls back `current`/`previous` pointers, and `scripts/deploy/shared_edge_renew.sh` performs unattended renewal with the success-only validated chain (`nginx -t` then container HUP). `make shared-edge-proof` proves the topology and runtime behavior locally; the proofs also run as part of `make production-proof` in CI.
- A checked-in `.env.example`: names and safe descriptions only.
- Non-secret production values live in GitHub Actions variables and sensitive values in GitHub Actions secrets. Each deploy transfers complete validated configuration to `/home/nuc/wef/secrets/releases/<git-sha>/` with mode `0600` and atomically updates `/home/nuc/wef/secrets/current`.

Persistent paths:

- `/home/nuc/wef/postgres/`.
- `/home/nuc/wef/media/`.
- `/home/nuc/wef/imports/` for operator-staged source data mounted read-only into importer runs.
- `/home/nuc/wef/caddy-data/`.
- A dedicated shared-edge root (operator-selected at edge deployment; `WEF_SHARED_EDGE_ROOT` must be supplied explicitly because it has no default) holding rendered releases with `current`/`previous` pointers, the ACME webroot, complete persistent Certbot `/etc/letsencrypt` state, deploy-hook state, and bounded edge logs. E7-T8 defines the boundary, E7-T10 confirms its live path, and it is not deleted with `/home/nuc/wef`.
- `/home/nuc/wef/releases/` for release metadata and Compose manifests.
- `/home/nuc/wef/secrets/releases/<git-sha>/` plus `secrets/current` for complete deploy-managed service configuration, including Telegram credentials; generated Telegram sessions persist under `/home/nuc/wef/secrets/telegram/`.

Application containers must not rely on writable container layers. Writable temporary paths use explicit temporary filesystems or project-owned volumes. Do not add explicit generic `container_name` values; Compose's `wef-production` prefix prevents collisions.

Before the first PostGIS start, a profile-gated one-shot service changes only the precreated WEF PostgreSQL bind root to the pinned image's UID/GID `999:999`. It runs with no network, a read-only root filesystem, and only `CHOWN`/`DAC_OVERRIDE`; this avoids sudo or broad host permissions. Inventory accepts the PostgreSQL root as either the inactive `nuc` owner or active UID 999 and rejects other WEF path ownership. The Caddy rollback edge runs as host UID/GID `1000:1000` on unprivileged internal port 8080, drops all default capabilities, and adds back only `NET_BIND_SERVICE` because the pinned binary carries that file capability; its WEF-owned data bind remains writable without another root initializer. Shared Nginx/Certbot owns the public boundary independently.

## Routing and TLS

Application Caddy rollback path:

- On port 3100, serves same-origin HTTP for anonymous smoke/browsing only.
- Routes `/api/*` to FastAPI and all other application routes to Next.js.
- Serves `/media/*` only from the dedicated public-derivative subtree mounted read-only; source media, restricted originals, and reports are absent from API/edge mounts.
- Remains available on `:3100` for rollback/diagnostics; it is not the public HTTPS entry and cannot establish production Secure-cookie sessions.

Live Nginx/Certbot edge:

- Nginx owns standard ports 80/443 for the WEF hostname and private WEF upstreams. AI Forecast remains outside this live edge on public port `3000`; a second vhost is only an optional fixture/future renderer mode.
- Certbot obtains free Let's Encrypt certificates, persists its complete state, renews unattended, and reloads Nginx only after successful renewal.
- HTTP redirects to HTTPS only after both application routes and certificates pass external smoke checks.
- [E7-T8](../epics/E7-production-delivery/tasks/E7-T8-build-shared-nginx-tls-ingress.md) delivered topology; [E7-T9](../epics/E7-production-delivery/tasks/E7-T9-implement-reversible-shared-edge-cutover.md) delivered cutover/rollback automation; [E7-T10](../epics/E7-production-delivery/tasks/E7-T10-roll-out-and-verify-shared-tls.md) completed DNS/router confirmation, live WEF cutover, renewal proof, monitoring, and rollback.
- [E7-T7](../epics/E7-production-delivery/tasks/E7-T7-enable-production-registration-and-contact-reveal.md) enabled authentication/contact reveal after the E7-T10 HTTPS gate.
- Full topology, certificate lifecycle, and evidence requirements are in [Nginx and TLS target](NGINX_TLS.md).

Both public and rollback routes:

- Preserve client/request IDs and correct proxy headers.
- Enable compression for text/JSON, not already compressed media.
- Add HSTS (`Strict-Transport-Security: max-age=31536000`) on the WEF HTTPS shared-edge vhost after the domain and certificate flow are verified (E7-T10). Omit `preload` unless separately approved. Do not advertise HSTS on plain `:3100`.
- Add `X-Content-Type-Options: nosniff`, a conservative referrer policy, and a tested Content Security Policy.
- The CSP explicitly permits only the configured map style/tile origins, same-origin API/media, and the worker requirements used by MapLibre (including `worker-src blob:` only when the chosen bundle requires it).
- Prevent directory listing and access to dotfiles or temporary media files.

PostgreSQL, web, API, media, and worker upstream ports remain on internal Compose networks. WEF must not take ownership of host ports 3000, 8080, or UDP 51820, and deployment must not restart or alter non-WEF projects. Published 80/443 and the retained `:3100` listener are rechecked by the respective preflight/inventory boundaries.

Shared Nginx is the only public WEF web server on 80/443. Ordinary WEF application deploys do not own, recreate, or remove the `wef-shared-edge` project. When the external `wef-edge` network is present, each deploy/rollback merges `compose.production-shared-edge.yaml` (keeping Caddy on `:3100`), runs `scripts/deploy/reconnect-wef-upstreams.sh` (attach `wef-api`/`wef-web`/`wef-media` + Nginx HUP), and must pass public HTTPS smoke on `WEF_PUBLIC_HTTPS_BASE_URL` (default `https://2fa54e2405.duckdns.org`) before activation. TLS templates use Docker DNS (`resolver 127.0.0.11`) with variable `proxy_pass` so upstream IPs re-resolve after container recreate; reconnect still attaches network aliases. AI Forecast remains unchanged by ordinary WEF releases.

## Server sizing baseline

The resolved NUC deployment uses this sizing guidance:

- Preferred: 4 vCPU, 8 GB RAM, and at least 80 GB SSD.
- Minimum for a low-traffic proof: 2 vCPU and 4 GB RAM if import/media processing is carefully bounded.
- Enough disk for source import, media migration, database growth, Docker images, and temporary derivatives.
- A current supported 64-bit Linux distribution with Docker Engine and Compose v2.

The build occurs in GitHub, reducing production CPU/RAM requirements. The full historical import and image derivative generation should be benchmarked before accepting a smaller server.

### Observed target host

Read-only inspection of `nuc@2fa54e2405.duckdns.org` on 2026-08-12 found:

- Ubuntu/kernel 6.8 on x86-64.
- Approximately 7.3 GiB RAM, 6.4 GiB available at inspection, and 4 GiB unused swap.
- A 936 GB root filesystem with approximately 877 GB available.
- Existing Compose projects `ai-forecast-production`, `duckdns-ddns`, and `wireguard`.
- Existing host bindings 3000/TCP, 8080/TCP, and 51820/UDP.
- Ports 80/TCP and 443/TCP were not listening at inspection time, but the deployment preflight must recheck rather than assume they remain free.
- The supplied `nuc` user has Docker access and interactive sudo but no passwordless sudo. Automation must not persist/administer that password, so WEF uses `/home/nuc/wef` and privileged firewall changes remain manual.

Before/after deployment snapshots of `docker compose ls`, running containers, bound ports, and health status must show that all pre-existing projects remain unchanged. Heavy full-data import/media processing should use bounded concurrency and resource limits so it cannot starve the shared host.

Complete inspected details and the transfer runbook are in the [production server baseline](SERVER.md).

## GitHub repository controls

- GitHub-enforced `main` protection is out of scope under [ADR-017](../decisions/adr/ADR-017-no-enforced-branch-protection.md); follow branch/PR/CI rules procedurally and do not claim technical enforcement.
- Use GitHub Actions variables for non-secret configuration and Actions secrets for sensitive configuration without depending on paid environment protection.
- Every successful merge/push to `main` automatically builds and publishes a release candidate.
- E7-T4 completed the rollback rehearsal; `AUTO_DEPLOY_ENABLED=true` is the current repository value (verified 2026-08-26). Automatic deployment still fails closed unless the exact SHA is associated with a merged PR and every release job succeeds.
- Grant each job minimum `permissions`.
- Pin third-party Actions to full commit SHAs; use Dependabot/Renovate to propose controlled updates.
- Enable secret scanning and dependency alerts.
- Apply the branch, hotfix, owner-bypass, and Dependabot policy in [Repository and change rules](../governance/REPOSITORY_RULES.md).
- Native protection-dependent auto-merge remains disabled; the custom merge controller and tested main-only deployment remain available.

Repository configuration (current non-secret values verified 2026-08-26):

- Variables: `AUTO_DEPLOY_ENABLED=true`, `DEPLOY_HOST`, `DEPLOY_SSH_PORT`, `DEPLOY_USER`, `POSTGRES_DB`, `POSTGRES_USER`, `WEF_BIND_ADDRESS`, `WEF_LOG_LEVEL`, and `WEF_PUBLIC_PORT`.
- Secrets: `DEPLOY_SSH_KEY`, `DEPLOY_KNOWN_HOSTS`, `POSTGRES_PASSWORD`, and
  `WEF_GEOAPIFY_API_KEY`.
- The `production` GitHub environment is a deployment audit boundary, not a paid approval/protection claim.
- The database password must be 24–128 characters from the workflow's documented dotenv-safe alphabet; generate it rather than reusing an account password.

## CI workflow

Pull requests run five stable checks:

1. `Backend` — format/lint/type/architecture, PostGIS tests with the 90% suite floor, deterministic OpenAPI, and Python dependency audit.
2. `Frontend and contract` — format/lint/type, Vitest with the 90% suite floor, OpenAPI/client/docs/compatibility checks, production build, dependency audit, and Playwright critical path.
3. `Repository safety` — scripts, Markdown links, Compose/topology proofs, and source/secret exclusions.
4. `Runtime images` — non-root runtime image builds/content inspection and the production runtime proof.
5. `Coverage badge` — independently enforces both suite floors and publishes the combined badge only on `main`.

A failed required job blocks merge.

Use deterministic fixtures and ephemeral databases. CI never receives production Telegram sessions, source media, server SSH keys, or the complete export.

## Release and deploy workflow

On a successful push to `main`:

1. Check out the exact commit.
2. Run or depend on the complete release lint/test/contract/build suite.
3. Authenticate to GHCR with the job-scoped `GITHUB_TOKEN`.
4. Build web and backend images once.
5. Tag both with the full commit SHA and attach OCI revision labels.
6. Push images to GHCR and capture their immutable digests.
7. Generate a release manifest containing SHA, digests, migration revision, and timestamp.
8. Query the GitHub API for a merged pull request targeting `main` associated with the pushed SHA.
9. Stop before SSH when `AUTO_DEPLOY_ENABLED` is not `true`, when the SHA lacks the merged-PR association, or when a required release job failed.
10. Connect over SSH as `nuc` using a dedicated project-scoped deployment key.
11. Build the complete release configuration from GitHub Actions variables/secrets without printing it; transfer it plus versioned Compose/Caddy/release metadata to mode-0600 temporary paths.
12. Run the remote deployment script under a host `flock` to prevent concurrent releases.
13. Validate configuration, atomically activate the release secret/config directory, and delete temporary transfer files on success or failure.
14. Pull the new image digests before changing running services.
15. Record the current release as `previous_release`.
16. Converge the required persistent media storage directories, rejecting symlinks and non-directory paths before any migration or application replacement.
17. Verify database connectivity, disk headroom, and configuration.
18. Run the operator-only Geoapify readiness command from the production host. It consumes one public-fixture request and fails closed without logging the key or provider payload.
19. Run forward-compatible Alembic migrations from the new backend image.
20. Start/update services with the new explicit release SHA/digests.
21. Wait for API readiness and test the public web, API, map shell, and a media URL.
22. Mark the release successful and retain redacted deployment logs.

The same workflow supports `workflow_dispatch` with an explicit tested SHA for the [E7-T4](../epics/E7-production-delivery/tasks/E7-T4-implement-health-verification-and-rollback.md) rehearsal and owner-authorized emergency deployment. Its explicit rollback-rehearsal input requires a different active SHA, lets the candidate pass real smoke, then injects a reviewed health-gate failure. Exit `42` counts as rehearsal success only after previous-release smoke, failure-state recording, and non-interference verification pass.

Do not prune the previous release's images until a newer deployment has also succeeded and retention permits removal.

## Registry authentication

GitHub Actions publishes with `GITHUB_TOKEN` and `packages: write`.

The production server pulls with one of:

- Anonymous pulls if packages are intentionally public.
- During GitHub deployment, the job-scoped `GITHUB_TOKEN` with `packages: read`; the workflow logs in immediately before pull, logs out in its exit trap, and the token expires with the job.
- A dedicated fine-grained/read-only package credential only if future operations must pull independently of GitHub Actions.

Do not copy the workflow's transient `GITHUB_TOKEN` into long-lived server configuration. Registry credentials are scoped to package read access and supplied to `docker login` without appearing in command logs.

## Database migrations

- Alembic has one linear production head unless a reviewed branch merge is required.
- CI upgrades an empty database and a representative previous schema to the new head.
- Deploy migrations are non-interactive and time-bounded.
- Destructive changes use expand/migrate/contract across releases.
- The previous application should tolerate the expanded schema until the new release passes health checks.
- A migration failure stops before application restart and leaves the existing release running where possible.
- Schema downgrade is not the default rollback mechanism.

Large data reprocessing is an explicit importer operation after deploy, not hidden inside an Alembic migration.

## Health verification

Deployment succeeds only when:

- All required Compose services are healthy.
- `/api/v1/health/live` and `/api/v1/health/ready` succeed through the application route and the public shared-Nginx HTTPS origin.
- The web root returns the expected release marker/header.
- A bounded map endpoint smoke query returns valid GeoJSON.
- A browser smoke check initializes MapLibre and loads the configured style/tile origin without Content Security Policy violations.
- A known test media asset is retrievable with the expected content type.
- The release SHA in web/API responses or diagnostics matches the manifest.
- Operators collect a redacted host summary with
  `python3 -m scripts.deploy.operator_diagnostics --root /home/nuc/wef`
  (release, last deploy failure, disk usage, last successful import aggregates).
  Never paste diagnostics that still contain secrets; the command redacts known
  sensitive keys, but review before sharing.
- The configured public MapLibre style document is reachable and has valid version/source/layer structure.

Health scripts use fixed, non-sensitive test data.

## Rollback

Application rollback:

1. Select `previous_release`.
2. Verify its images still exist locally or in GHCR.
3. Apply the previous Compose release manifest.
4. Restart web/API/worker as needed.
5. Verify the same health suite.
6. Record the failed and restored releases in mode-0600 `last-failure.json`, including only candidate/restored SHA, reason, and UTC timestamp.

Database rules:

- Automatic application rollback assumes the migration was backward compatible.
- If data integrity is at risk, stop writes/worker first.
- No data restore path exists in the initial scope; [ADR-015](../decisions/adr/ADR-015-defer-backups.md) accepts that risk.
- Never run an unreviewed automatic Alembic downgrade in production.

The public API is read-only, but ingestion is a write workload. Pause the Telegram worker during any recovery that could race with restored state.

## Secrets and configuration

GitHub repository variables provide `DEPLOY_HOST`, `DEPLOY_SSH_PORT`, and `DEPLOY_USER`. Secrets provide `DEPLOY_SSH_KEY` and `DEPLOY_KNOWN_HOSTS`.

GitHub Actions variables/secrets transferred on every deployment:

- Database name/user/password or URL.
- Site domain and environment.
- Auth session/admin-session secrets and contact encryption/HMAC keys.
- One-time owner bootstrap username/password only until the first owner is persisted; remove/rotate it afterward.
- GHCR read credential when required.
- Production geocoder credentials/contact configuration.
- Telegram API ID/hash/session/phone through `WEF_TELEGRAM_API_ID`, `WEF_TELEGRAM_API_HASH`, `WEF_TELEGRAM_SESSION`, and `WEF_TELEGRAM_PHONE`; non-secret channel identity comes from application settings.

Practices:

- Verify SSH host keys; do not disable strict host checking.
- Use the supplied non-root `nuc` account with a dedicated project-scoped SSH key; it has Docker access, which is effectively privileged and must be tightly protected.
- Keep secret files mode `0600` and directories appropriately restricted.
- Treat GitHub Actions variables/secrets as the deployment source of truth; transfer a complete validated config each release and activate it atomically.
- Keep only the active and immediately previous release configuration required for application rollback; delete transfer temporaries on success/failure.
- Prefer service-scoped mounted secret files; support `_FILE` configuration.
- Never interpolate secrets into generated public frontend assets.
- Redact secrets from shell tracing, Compose output, reports, and logs.
- Rotate a Telegram session as a security credential, not as ordinary configuration.
- Keep registration/contact reveal disabled on plain HTTP; production auth cookies require HTTPS.

## Persistent application data

PostgreSQL/PostGIS is the canonical store for source messages/revisions, normalized locations, developments, offers, geocode cache, media metadata, ingest runs, and Telegram checkpoints. It runs in WEF's own container and writes to `/home/nuc/wef/postgres/`; it never shares the existing AI Forecast PostgreSQL container.

Restricted originals live under `/home/nuc/wef/media/originals/`; generated public derivatives live under `/home/nuc/wef/media/public/`; reports live under `/home/nuc/wef/media/reports/`. Only `media/public` is mounted into API/edge containers. After historical candidate activation (E7-T11), `media/public` and `media/originals` may be symlinks into `/home/nuc/wef/candidates/<checksum>/media/{public,originals}`; deploy preflight and inventory checks allow those contained candidate targets and still reject other runtime symlinks. Every stored object is referenced by an opaque database key. Historical import files may be transferred under `/home/nuc/wef/imports/`, mounted read-only only into operator commands, and removed independently after verified import.

The live Telegram worker writes a database transaction before advancing its checkpoint, so container restart/redeploy does not lose acknowledged state. Its session secret persists separately under `/home/nuc/wef/secrets/` and is not part of the database or repository.

None of these paths is committed to Git, copied into an image, or stored on a container's writable layer.

## Backups

Backups and restore drills are out of scope under [ADR-015](../decisions/adr/ADR-015-defer-backups.md). PostgreSQL, media, imports, Caddy rollback state, and secrets persist on the NUC only. Shared Nginx configuration and complete Certbot state also persist on the NUC under their independent edge boundary.

This is persistence, not backup: one disk/host failure, corruption, accidental deletion, or destructive migration may permanently lose all application data. Future backup work must add encrypted off-server copies, retention, and restore verification before claiming recovery guarantees.

## Telegram worker operations

The local worker remains behind the `telegram-worker` profile. Production release `3ee56a5` created and started the `telegram-worker` service on 2026-08-26 using deploy-managed environment credentials and the persistent restricted session directory. Operators use `wef-verify-telegram-channel` for redacted identity/credential readiness, `wef-telegram-backfill` for bounded overlap backfill, and `wef-telegram-worker-status` for checkpoint reconciliation, liveness, and rotation rehearsal. Missing/invalid credentials fail closed. On 2026-08-27, however, a connected and Docker-healthy worker remained at checkpoint `29202` while Telegram advanced through at least `29257`; the status command reported stale but local reconciliation remained internally aligned. E15-T1 replaces transport-only health with fail-fast transport/consumer/health/reconciliation-slot supervision and privacy-safe stage diagnostics while preserving the legacy heartbeat for rollback. Its reconciliation slot is explicitly pending—not evidence of completeness—until E15-T2 adds independent checkpoint polling and remote-gap detection. D-003/B-003 remain open through production recovery. Recurring geocoding retains Geoapify under resolved D-002.

On cancellation or critical-stage failure, the supervisor cancels sibling tasks and
removes both local health files. An in-flight database transaction rolls back through
the existing persistence/session boundary; queued passive events that never committed
do not advance the durable checkpoint. Until E15-T2 supplies automatic polling, those
unacknowledged events remain recoverable through the existing bounded backfill path.

After historical activation, imported offers may remain `needs_review` while the M1 synthetic seed is still `visible`. Run `wef-promote-public-catalog` in the API/operator container to hide synthetic seed rows and publish historical offers (`needs_review` → `visible`). Map pins still require an accepted in-scope location with coordinates. When geocode results exist but auto-review left locations unpinned (`low_precision` / `low_confidence`), run `wef-accept-pending-geocode-pins` to copy in-scope coordinates onto those locations with `manual_accept` lineage (AD-034). Out-of-scope and provider `no_result` rows stay unpinned.

When enabled:

- Run exactly one replica per configured channel.
- Use `restart: unless-stopped` plus an application reconnect loop with bounded backoff.
- Mount the persistent Telegram session directory only into the worker, not web/API.
- Depend on database readiness, not API readiness.
- Persist checkpoints before acknowledging progress.
- Expose no public port.
- Include last committed message/event time in internal health diagnostics.
- Alert when the connection/checkpoint is stale beyond an agreed threshold.

Deploy behavior:

- Pause/restart the worker around migrations only when schema compatibility requires it.
- On application rollback, use a backend image compatible with the current schema.
- Backfill overlap after downtime; source idempotency absorbs duplicates.

Session rotation:

1. Stop the worker.
2. Generate/authorize a new session in a controlled environment.
3. Replace the secret atomically.
4. Start and verify entity identity/checkpoint.
5. Revoke the old Telegram authorization.
6. Confirm a small overlap reconciliation.

More source semantics are defined in the [ingestion pipeline](../ingestion/PIPELINE.md).

## Monitoring

Current monitoring baseline:

- External HTTPS uptime checks for WEF; AI Forecast remains independently reachable on `:3000`, while `:3100` is a WEF rollback/diagnostic route.
- Host disk, memory, CPU, load, and Docker restart count.
- TLS chain/hostname/expiry, Certbot renewal, and Nginx reload checks.
- Telegram transport timestamp plus versioned critical-loop health, last committed event,
  and checkpoint reconciliation; these never gate public API readiness. A
  `pending_implementation` reconciliation stage is not source-completeness evidence.
- Structured logs retained with size/rotation limits.

Alert first on user impact, disk exhaustion risk, database unready state, and stale Telegram ingestion. Do not add a large metrics platform before these basic checks are operational.

## Server handoff checklist

Before the first production deployment, collect:

- Distribution/version, architecture, CPU, RAM, disk layout, and free space.
- Public IP, SSH port, deploy username, sudo/Docker policy, and host key.
- Domain and DNS control.
- Firewall and provider security-group rules.
- GHCR package visibility preference.
- Geocoder provider decision.
- Telegram channel username/entity and access details only when [Epic 8](../epics/E8-telegram-live-ingestion/README.md) begins.

Then:

- Patch the host and configure time synchronization.
- Verify the already-installed Docker 29.5.1 and Compose 5.1.3 versions; do not reinstall during application deployment.
- Create `/home/nuc/wef` project directories owned by `nuc` and install a dedicated deployment SSH key for that account.
- Keep SSH and `WEF_PUBLIC_PORT=3100` as the rollback path; public 80/443 forwarding is assigned to the WEF-only Nginx/Certbot edge, while AI Forecast remains on `:3000`.
- Configure swap only if appropriate for host memory; never use it to hide undersizing.
- Verify both DNS names before enabling Nginx production TLS or changing the existing port-3000 route.
- Rehearse the first release on production infrastructure with synthetic/empty data; do not create a staging environment.

## Ongoing public production readiness gate

The initial gate is complete; every later release must preserve it.

- Required CI is green for the exact release.
- Images are immutable and vulnerability policy passes.
- Server configuration validates without default secrets.
- DNS/TLS and SSH host verification are complete.
- Database migration upgrade tests pass.
- Health checks and rollback to the previous application release have been rehearsed.
- Export/media paths are not present in image layers or Git history.
- OpenStreetMap attribution, anonymous contact masking, and authenticated reveal auditing are verified.
- Telegram worker failures remain isolated from public readiness; live acceptance and reconciliation evidence stay tracked separately under M4 until complete.
