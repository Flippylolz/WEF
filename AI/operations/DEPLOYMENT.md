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
- `telegram-worker`: optional local listener. Enable with `docker compose --profile telegram-worker` after `WEF_TELEGRAM_API_ID` and `WEF_TELEGRAM_API_HASH` are set in the gitignored repo-root `.env`. The worker generates a Telethon string session on first login (`WEF_TELEGRAM_PHONE`, then `WEF_TELEGRAM_LOGIN_CODE` if not a TTY) and persists it to `WEF_TELEGRAM_SESSION` / `secrets/telegram/session`. Compose healthchecks both the backward-compatible transport timestamp and the versioned critical-loop runtime-health document via `wef-telegram-worker-status --liveness` (never gates `/api/v1/health/ready`). Reconciliation defaults to 60 seconds, 100-message batches, a 500-message cycle cap, and a 20-message overlap; override with the corresponding `WEF_TELEGRAM_RECONCILIATION_*` variables only within their validated bounds. Observe remote/local gap and freshness with `wef-telegram-worker-status`. Rehearse rotation with `wef-telegram-worker-status --rotation-dry-run`.

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
- `telegram-worker`: one replica. Host env comes from the deploy-managed `production.env` (`WEF_TELEGRAM_API_ID`, `WEF_TELEGRAM_API_HASH`, optional `WEF_TELEGRAM_SESSION` / `WEF_TELEGRAM_PHONE`, plus `WEF_GEOAPIFY_API_KEY` for the supervised `recurring_geocode` loop). Generated sessions persist under `${WEF_ROOT}/secrets/telegram/` (mode 0700). Ordinary production deploys start the worker after API/web/edge; the container healthcheck requires fresh transport, serialized-consumer state, and reconciliation completed within three minutes. The worker geocodes pending live locations every 60 seconds (default), accepts in-scope pending pins, and promotes map-ready offers without gating public readiness.

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

- GitHub branch protection enforces the `main` pull-request, strict CI, conversation-resolution, linear-history, force-push, and deletion rules under [ADR-023](../decisions/adr/ADR-023-enforce-main-branch-protection.md). Approving reviews are not required while the owner is the sole maintainer. The merged-PR release check remains defense in depth for the audited administrator exception.
- Use GitHub Actions variables for non-secret configuration and Actions secrets for sensitive configuration without depending on paid environment protection.
- Every successful merge/push to `main` automatically builds and publishes a release candidate.
- E7-T4 completed the rollback rehearsal; `AUTO_DEPLOY_ENABLED=true` is the current repository value (verified 2026-08-26). Automatic deployment still fails closed unless the exact SHA is associated with a merged PR and every release job succeeds.
- Grant each job minimum `permissions`.
- Pin third-party Actions to full commit SHAs; use Dependabot/Renovate to propose controlled updates.
- Enable secret scanning and dependency alerts.
- Apply the branch, hotfix, owner-bypass, and Dependabot policy in [Repository and change rules](../governance/REPOSITORY_RULES.md).
- Repository-level native auto-merge is enabled as an opt-in convenience and cannot bypass protected-branch gates. The custom merge controller remains authoritative for Dependabot-specific eligibility, and tested main-only deployment remains available.

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

Optional Groq catalog-curation settings (`WEF_AI_CURATION_ENABLED`, `WEF_GROQ_API_KEY`,
`WEF_GROQ_MODEL`, `WEF_GROQ_ZDR_VERIFIED`, `WEF_GROQ_TIMEOUT_SECONDS`,
`WEF_GROQ_USE_BATCH_API`, `WEF_GROQ_BATCH_CHUNK_SIZE`,
`WEF_GROQ_BATCH_POLL_INTERVAL_SECONDS`, `WEF_GROQ_BATCH_MAX_WAIT_SECONDS`) must **not** be
added to `validate_release` `REQUIRED_KEYS`. Missing values keep AI review absent
and must not fail deploy or `/api/v1/health/ready`. When `WEF_GROQ_API_KEY` is present
in GitHub Actions secrets, `build_release_config` includes those optional keys in the
transferred `production.env`; enablement flags come from Actions variables and stay
`false` until the owner completes ZDR proof.

## Groq AI curation operations

Owner of the Groq secret and Zero Data Retention proof: the repository/product owner.
Do not recover or reuse the previously removed OpenAI key.

Activation (all required; fail closed otherwise):

1. Confirm Groq Zero Data Retention is verified for this account and set
   `WEF_GROQ_ZDR_VERIFIED=true` only after that proof exists.
2. Store `WEF_GROQ_API_KEY` as a GitHub Actions secret / production secret file, never
   in git.
3. Keep `WEF_GROQ_MODEL=openai/gpt-oss-20b` (exact allowlist).
4. E25 revision 2 uses durable single-item Chat Completions for all composed
   owner and scheduled work under ZDR. The legacy `WEF_GROQ_USE_BATCH_API` flag
   does not select provider Batch/Files. Manual and scheduled operations share
   20 generation items per owner/UTC day, one in-flight item and 60-second pacing.
   Drain old writers before cutover; retained daily usage initializes the ledger.
5. Set `WEF_AI_CURATION_ENABLED=true` last.
6. Attach the **`api` service to `provider-egress`** in production Compose (merged
   #241). Without it, Groq HTTPS/DNS from `api` fails even when secrets are present.

Until those gates are complete, `/admin/places` omits **Review with AI**. Existing
location administration continues.

For clearing the historical `ungeocoded` backlog with place review, see
[Ungeocoded backlog and AI-assisted recovery](../ingestion/UNGEOCODED_BACKLOG_AND_AI_RECOVERY.md).

Backend operator CLIs (`wef-batch-ingestion-ai-parse`, `wef-backfill-parse-issues`,
`wef-accept-pending-geocode-pins`, and related commands) are catalogued in
[OPERATOR_COMMANDS.md](OPERATOR_COMMANDS.md) with container placement, flags, and
production compose examples.

Smoke after a release that includes the console (do not mutate real offers):

- `/api/v1/health/live` and `/api/v1/health/ready` succeed without Groq.
- Owner login can open `/admin/places`.
- When the feature is off, **Review with AI** is absent.
- Do not click generate/apply against production places merely to demonstrate the
  feature.

Free-tier monitoring: the backend enforces 20 provider requests per owner per UTC
day. Watch Groq dashboard remaining credits/rate limits privately; never log API
keys, prompts, source bodies, or provider error payloads.

Disable: set `WEF_AI_CURATION_ENABLED=false` (or remove the key / set ZDR false) and
redeploy or restart API. In-flight HTML actions fail closed. Rollback is the prior
immutable image; unused `place_ai_review_runs` rows are inert.

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

The local worker remains behind the `telegram-worker` profile. Production release `3ee56a5` created and started the `telegram-worker` service on 2026-08-26 using deploy-managed environment credentials and the persistent restricted session directory. Operators use `wef-verify-telegram-channel` for redacted identity/credential readiness, `wef-telegram-backfill` for bounded overlap backfill, and `wef-telegram-worker-status` for checkpoint reconciliation, liveness, and rotation rehearsal. Missing/invalid credentials fail closed. On 2026-08-27, however, a connected and Docker-healthy worker remained at checkpoint `29202` while Telegram advanced through at least `29257`; the status command reported stale but local reconciliation remained internally aligned. E15-T1 added fail-fast critical-loop supervision and privacy-safe stage diagnostics. E15-T2 release `7184cc2d67a` adds an immediate and 60-second checkpoint polling loop plus remote-head/local-checkpoint gap status, making passive events a latency path rather than the completeness boundary. E15-T3 reconciled every source ID through observed head `29335`, proved an identical replay made no canonical changes, and rehearsed restart plus worker-health fire/clear while public readiness stayed available. Exact redacted evidence is in [E15 production recovery evidence](../epics/E15-telegram-ingestion-reliability/PRODUCTION_EVIDENCE.md). D-003/B-003 now retain only real passive new/edit/delete and live media acceptance; recurring geocoding retains Geoapify under resolved D-002.

On cancellation or critical-stage failure, the supervisor cancels sibling tasks and
removes both local health files. An in-flight database transaction rolls back through
the existing persistence/session boundary; queued passive events that never committed
do not advance the durable checkpoint. The restarted worker immediately polls from that
checkpoint, so the unseen suffix remains recoverable without a full historical import.

Each reconciliation cycle observes the remote head, replays a 20-message overlap, sorts
messages by source ID, writes through the existing idempotent live processor in batches
of at most 100, and processes no more than 500 messages. The next cycle continues when
the remote head remains ahead. Existing Telethon flood-wait handling applies. Polling
never treats absence as deletion; only passive delete events change deletion state.

After historical activation, imported offers may remain `needs_review` while the M1 synthetic seed is still `visible`. Run `wef-promote-public-catalog` in the API/operator container to hide synthetic seed rows and publish historical offers (`needs_review` → `visible`). Map pins still require an accepted in-scope location with coordinates. When geocode results exist but auto-review left locations unpinned (`low_precision` / `low_confidence`), run `wef-accept-pending-geocode-pins` to copy in-scope coordinates onto those locations with `manual_accept` lineage (AD-034). Out-of-scope and provider `no_result` rows stay unpinned.

When enabled:

- Run exactly one replica per configured channel.
- Use `restart: unless-stopped`; transport exit is fail-fast and the restarted process
  performs immediate checkpoint reconciliation.
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
  last successful reconciliation, observed remote head, durable local checkpoint, and
  remote-gap flag; these never gate public API readiness.
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

## Release outcome evidence (E27-T1)

The release workflow writes `wef-release-outcome/v1` JSON and an Actions summary
in the always-run **Release outcome** job. The artifact is named
`release-outcome-<run_id>-<run_attempt>` and retained for 90 days. It is reporting
only, never deployable artifact evidence. The existing release artifact retains
its 14-day lifetime.

`verified_only` means verification succeeded but the deployment gate rejected the
run; its reason distinguishes missing merged PR association and disabled automatic
deployment. `deployed` requires host smoke and activation timestamps for the exact
SHA. `already_current` is a duplicate observation, not a fresh release.
`failed_restored` identifies the failed candidate and restored healthy SHA.
`failed`, `verification_failed`, `preparation_failed`, `queued`, `superseded`, and
`deployment_unconfirmed` remain distinct. Also inspect `deployment_job_result`:
a post-activation inventory/bootstrap failure can fail the job after the release
became healthy.

Host observations are run-attempt-specific mode-0600 files, exported through an
allowlist and removed after successful collection. Optional observation failure
cannot interrupt deployment or rollback. Missing/cancelled/unavailable evidence
is null with a reason, never fabricated success. A hard workflow cancellation can
prevent the report job; use the Actions run conclusion as cancellation evidence
and do not rerun activation merely to obtain a report.

Timings include per-job/per-step intervals, initial event-to-first-job delay,
unattributed job time, and gaps between job intervals. Overlapping intervals are
counted once. Gaps include dependencies and runner waits; the API does not always
identify those separately. Cache evidence uses observed component counters; missing
counters remain explicitly unknown (see E27-T3 below).
Merge-to-healthy uses the matching merged PR timestamp and host-observed smoke
success, an upper bound on first healthy service. Failed, superseded and duplicate
releases have no fresh-release latency. Existing health/configuration/rollback
and associated-PR gates are unchanged by reporting.

## Shared verification and release serialization (E27-T2)

PR CI and the main-push release call `.github/workflows/verify.yml` with the
exact source SHA. Backend, frontend and repository verification run independently;
backend tests use one disposable host PostGIS service. The release no longer
runs a duplicate main-push CI workflow or builds Compose test images after
installing the same host dependencies. PR status adapters preserve the protected
names `Backend`, `Frontend and contract`, `Repository safety`, `Runtime images`,
and `Coverage badge`; none can pass from skipped/failed shared verification.
Coverage publishing consumes successful main-push release runs instead of CI.

The shared runtime-image action checks source identity, builds with existing
component cache scopes, and inspects runtime users/contents. PR runs have no
publish credentials or package-write permissions. Release backend/web images
build independently alongside verification, then the exact published digests
pass the production runtime/persistence proof. Only the complete verification,
image and runtime dependency graph can assemble a deployable release artifact.
[The parity record](../epics/E27-faster-verified-releases/CHECK_PARITY.md) maps
all previous checks to this graph.

A per-SHA workflow concurrency group prevents duplicate requests from preparing
the same release simultaneously. The `wef-production` group covers the entire
deployment job, from private configuration and transfer through health,
rollback, inventory, bootstrap, registry logout and cleanup; cancellation of an
active release remains disabled. Different SHAs can verify and build concurrently.
GitHub can replace a pending concurrency entry; a cancelled candidate is not a
successful release. Queue order is never treated as source order.

An ordinary manual repeat can reuse a successful same-repository main-push run
only after checking its exact SHA, complete job results, unexpired artifact,
verification fingerprint, immutable digests and complete checksum inventory.
Missing/expired/invalid evidence falls back to full verification. Rehearsal flags
force fresh verification and cannot silently become no-ops. Both fallback and
reused artifacts are validated again before deployment. The fingerprint binds
verification workflow/action definitions and lockfiles to the caller's workflow
revision. It does not grant older source revisions an exemption from current
checks. No PR-head artifacts are reused for a merge SHA.

Under the production lock, snapshot current state and immutable digests, verify
source ancestry, and skip a candidate older than the current healthy release.
Unrelated history or inconsistent state fails closed. Repeat the current-state
comparison under the host lock immediately before migration. A same-SHA request
becomes `already_current` only with matching digests, identical configuration,
and successful local/public health proofs. Same-SHA configuration changes fail
comparison and require the existing explicit configuration-management path.

Transfers retry at most three times (immediately, after 5 seconds and after 15
seconds); migration/activation is never blindly retried. Before guarded mutation,
`state/activation-pending.json` records uncertainty durably. Verified activation
or verified rollback removes it. An interrupted or failed migration leaves the
marker and prevents the next release from silently repeating an ambiguous
mutation. Reconcile actual health, current/previous state, schema revision and
host-lock ownership before clearing it through an authorized recovery decision;
removing the marker alone is not evidence of recovery. A failed snapshot holding
the host lock also detects an orphaned remote deployment after SSH/runner loss.

Rollback restores the prior workflow through a reviewed change, retaining
observations and immutable releases. Do not cancel a running migration or rewind
production data. Existing off-host backup deferral still limits destructive data
recovery. No production fault injection is included in E27 acceptance.

## Release budget and cache evidence (E27-T3)

`python3 -m scripts.deploy.release_cohort --optimized-from FULL_MERGED_SHA
--limit 100 --output /private/tmp/wef-release-cohort.json --require-budget`
collects read-only GitHub metadata and sanitized outcome artifacts. Run this as
one command with the full merged optimization SHA. It writes JSON and Markdown;
`--input` can summarize a saved sanitized file without network access. A changed
cutoff requires fresh collection so ancestry is rechecked. Retain successive
sanitized snapshots if more than 100 runs occur before acceptance.

The collector counts at least 20 distinct eligible ordinary source SHAs with
observed deployment health, uses nearest-rank p50 <= 300 seconds and p95 <= 420
seconds, and includes queue time from the merged PR timestamp. Same-SHA retries
count once, using their earliest observed health since merge. Manual, unmatched,
verified-only, duplicate, superseded and failed runs remain visible but cannot
supply a successful fresh-release sample. Successful deploy-job completion is
reported separately and never substituted for health. Missing evidence, an
unknown cutoff or too few samples returns a nonzero result with
`--require-budget`; it does not dispatch another release.

Backend dependency-cache evidence is the pinned setup-uv action's `cache-hit`
output. Backend/web image evidence is the exact Buildx build record's completed
step and cached-step counts. Only these numeric counters leave the record;
inputs, environment and raw build records are not copied into outcome artifacts.
Image `warm` means at least one cached step, not a fully cached build. Component
states are retained, with an aggregate `warm`, `cold`, `mixed`, or `unknown`;
missing counters and reused artifacts stay unknown. Frontend host dependency
installation currently has no separate restore cache and is not labeled warm.
Cache observations cannot authorize reuse or bypass any verification gate.

The budget result is only latency evidence. Independently record consecutive
merge ordering, cold/warm cases, exact healthy SHA and digests, rollback and
shared-host proofs, provider/runner incidents, and operator interventions.
Workflow events cannot establish zero SSH/configuration interventions. Do not
silently exclude slow provider incidents or create production deploys to fill
the sample. The [acceptance record](../epics/E27-faster-verified-releases/ACCEPTANCE.md)
tracks measured facts and outstanding operational proof.

## E24-T1 original-archive recovery

The additive `20260905_0020` migration creates original-event receipts, source
tombstones, and channel recovery state. Before an authorized release, stop the
old archive worker so it cannot resume the lossy replay loop. Deploy migrations
and the corrected worker together. The operator interface, executed within the
backend runtime with its existing restricted configuration, is:

- `python -m wef_backend.archive_recovery_command` — read-only aggregate preflight.
- `python -m wef_backend.archive_recovery_command pause` — persist the archive pause.
- `python -m wef_backend.archive_recovery_command resume` — resume/verify its canary.
- `python -m wef_backend.archive_recovery_command apply` — apply at most one due 25-record batch.

The worker automatically starts a durable canary of up to 100 original rows and
expands only after receipt verification. Every batch reserves a five-second
interval; restarts and operator apply share that limit. Canary failure persists a
safe pause reason for investigation. Later arrivals still run after an empty
startup. No per-record approval is part of routine operation.

Preflight separates eligible/exhausted records, oldest pending age, candidate
terminal siblings, ready receipt projections, and canonical evaluations. Sibling
counts alone do not authorize acknowledgement. Detailed transition evidence stays
in PostgreSQL; do not commit payloads, contacts, UUID/checksum exports, or generated
source reports. Acknowledgement-only recovery makes no provider calls.

After release authorization, record a fixed 15-minute original cohort and its
completed/remaining counts separately from new arrivals and failures. Reconcile
receipts, unchanged source checksums, and stable terminal attempt counts. The
historical 27,656 eligible records are an audit baseline, not a current count or a
count of missing offers. Production acceptance remains pending until observed.

On evidence mismatch, pause and investigate the retained receipts. Never reset
cursors, delete siblings, clear the entire pending queue, or roll back to a worker
that ignores pause and restarts the known loop. Migration downgrade fails closed
when recovery evidence is populated; keep the additive schema and roll forward.
This procedure does not establish an off-host backup or complete T2–T4.

## E24-T2 progress and retry rollout

Apply additive revision `20260905_0021` after E24-T1's `20260905_0020`, then deploy
the matching worker. Keep the bounded T1 canary and pause controls authoritative.
Do not initialize polling from the highest stored source ID: existing evidence
bootstraps applied progress only. Polling begins at zero and the old-ID sweep
retains its own continuation. Compare operator `applied_high_water_id`,
`polled_through_id`, and `history_limited` with the corresponding runtime fields;
the legacy local checkpoint means polling coverage, not latest finished run.

Observe pending and quarantined work alongside polling progress. The forward
cursor may advance over a durably deferred item, but pending canonical work keeps
coverage limited. Next-attempt and source retry-after times survive restarts;
normal contention needs no operator reset. The restricted exception table retains
one original-event reference and safe reason for data exhaustion. Only a relevant
retry-policy revision reopens that budget automatically.

On rollback, pause the affected worker and retain the progress, retry counters,
due times, exception records, and T1 receipts. The migration refuses downgrade
when recovery evidence exists. Never reset these tables or restore the prior
run-completion cursor reader. Resume with a corrected compatible worker. These
are implementation/rollout instructions; production recovery has not yet been
measured for this change.

### E24-T2 temporary staging correction

Keep the Telegram worker paused while deploying the approved staging correction.
Do not enlarge `/tmp`, reset cursors, or delete source/media evidence to conceal
heartbeat failures. The corrected downloader reserves 56 MiB total with 8 MiB
free-space headroom, streams polling work, and releases exclusively owned files
after their consumer finishes. Resume with the existing archive-recovery control
after the release health checks pass. Observe at least 15 minutes with no worker
restarts, bounded `/tmp` use, advancing polling/sweep boundaries, continuing
original-cohort completions, and unchanged receipt/source invariants. Persist
pause and stop the affected worker again if systemic failure recurs.

The worker's file-only liveness CLI must remain independent of database/ORM
imports. Full operator status loads those dependencies only when requested; the
healthcheck timeout and freshness criteria are unchanged. A fresh-process test
blocks ORM imports while verifying both healthy and stale heartbeat exit codes.
