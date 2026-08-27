# Warsaw Estate Platform

[![Repository coverage](.github/badges/coverage.svg)](.github/workflows/ci.yml)

Warsaw Estate Platform (WEF) turns a Telegram real-estate export into a filterable map of Warsaw developments and offers.

## Current status

The historical Warsaw catalog is live at [2fa54e2405.duckdns.org](https://2fa54e2405.duckdns.org) behind the shared Nginx/Let's Encrypt edge. The shipped product includes backend-authoritative grouped-map queries, URL-backed and server-defined quick filters, dated offer detail and media, pseudonymous accounts, favorites, audited contact reveal, and the owner console. The complete historical import, Geoapify-backed geocoding, media pipeline, immutable GitHub deployment, health-gated rollback, and production diagnostics are implemented.

The Telethon new/edit/delete pipeline, restartable backfill, worker status, and production worker service are also implemented. M4 remains open until verified live entity/event delivery, gap reconciliation, and outage-recovery evidence close B-003; historical data remains available if the worker is unavailable.

Start with:

- [AI documentation index](AI/README.md)
- [Architecture](AI/architecture/README.md)
- [E0 proof report](AI/epics/E0-architecture-dependency-spike/PROOF_REPORT.md)
- [Epics and task dependencies](AI/epics/README.md)
- [Approval-gated workflow](AI/workflow/README.md)
- [Repository and change rules](AI/governance/REPOSITORY_RULES.md)

## Stack

- Python, FastAPI, SQLAlchemy, PostgreSQL, and PostGIS
- TypeScript, Next.js, React, and MapLibre
- Docker Compose with Caddy for local same-origin development and a shared Nginx/Certbot production edge
- GitHub Actions and GitHub Container Registry

The backend is authoritative for business behavior. The frontend primarily renders generated API contracts and backend-provided projections.

## Development

Prerequisites are Python 3.13.2, Node.js 22.22.2, uv, Corepack/pnpm, and Docker. Versions are recorded in `.tool-versions` and lockfiles.

```shell
make install
make format-check lint typecheck test contract-check
make coverage
make build
```

`make test-backend` and `make test-frontend` run the suites independently.
`make test` runs backend tests, then frontend tests. Backend tests are fully
containerized: they start local Compose PostGIS, recreate a reserved `wef_test`
database alongside the persistent development database, and need no host
database URL. Frontend unit tests run in the web development container with
no network. Each suite fails when its own branch-aware coverage is below 90%.
The coverage badge still shows the combined percentage, but that combined
figure is not a merge gate. `make coverage-backend` and `make coverage-frontend`
refresh each report; `make coverage` then writes the badge. GitHub Actions
publishes the badge on `main` only after both suite floors are met.

Static API documentation is generated as an artifact and is not served by the
production API.

`make help` lists the exact command façade. The Makefile delegates to uv, pnpm, and Docker; it does not select environments or contain application logic.

## Local Docker Compose

Docker with Compose v2 is the only prerequisite for the isolated local stack. Optional overrides can be copied from `.env.example` to an ignored `.env`.

```shell
make compose-config
make up
make seed-m1
curl --fail http://127.0.0.1:3100/api/v1/health/live
curl --fail 'http://127.0.0.1:3100/api/v1/map/locations?bbox=20.7%2C52.0%2C21.4%2C52.4'
make down
```

Only Caddy publishes a host port, bound to loopback on `3100` by default. The API, web process, PostGIS, and operator container remain on an internal network. `make down` preserves the named database and media volumes.

This is the local topology. Production keeps the internal application Caddy listener on `:3100` as a rollback path and serves the public site through the independently managed shared Nginx/Certbot edge on `:443`. See [deployment operations](AI/operations/DEPLOYMENT.md).

`make up` applies forward Alembic migrations before API startup. `make seed-m1` explicitly converges a small invented Warsaw fixture for map/API verification; production requires a separate explicit rehearsal opt-in and the command never reads the local export.

Open `http://127.0.0.1:3100/` after seeding. The public map style defaults to keyless OpenFreeMap and can be replaced at image-build time with `NEXT_PUBLIC_MAP_STYLE_URL`; OpenFreeMap/OpenStreetMap attribution remains visible in the map shell.

`make importer-dry-run` starts the operator profile, confirms that
`WEF_SOURCE_DIR` is mounted read-only, streams the configured historical export
through the rule-bound E2 parser, and atomically writes detailed JSON/Markdown
reports plus privacy-safe aggregate audit evidence below the configured ignored
report destination. It prints only terminal status/counts and performs no
database/geocode/media write, media copy, or network request.

## Resumable historical import

After exporting Telegram as machine-readable JSON, point the ignored local
configuration at the directory containing `result.json` and run the incremental
preview before any canonical write:

```shell
WEF_SOURCE_DIR=/absolute/path/to/export make import-dry-run
```

The preview scans and validates the complete immutable snapshot, displays a
terminal progress bar, and reports exact new, changed, unchanged, candidate,
media, and pending-geocode counts. It does not write canonical rows, copy media,
or call a provider. Stable Telegram channel/message identity plus the per-record
checksum means a later dump processes only unseen or changed messages while
retaining every prior revision.

Run all stages, or operate them independently:

```shell
WEF_SOURCE_DIR=/absolute/path/to/export make import-persist
WEF_SOURCE_DIR=/absolute/path/to/export make import-geocode
WEF_SOURCE_DIR=/absolute/path/to/export make import-media
WEF_SOURCE_DIR=/absolute/path/to/export make import-verify

# Equivalent staged sequence; stops cleanly when a configured provider limit pauses it.
WEF_SOURCE_DIR=/absolute/path/to/export make import-run
```

Persistence defaults to 200-record transactions. Geocoding is cache-first,
checkpoints every 25 locations, reserves every hosted attempt before network I/O,
spaces calls globally at four per second, and stops at the durable 2,700-attempt
UTC-day safety cap. `IMPORT_BATCH_SIZE`, `IMPORT_GEOCODE_BATCH_SIZE`, and
`IMPORT_MAX_PROVIDER_REQUESTS` bound one invocation. Interrupted work is safe to
rerun: database/cache/media replay identities determine unresolved work, while a
five-minute fenced lease prevents overlapping owners after a crash. Provider
credentials stay in ignored `.env`/runtime secrets; output contains aggregate
counts and opaque run IDs only.

The inert production model is separate from local Compose:

```shell
make production-proof
```

That command renders the digest-only `wef-production` topology, validates the Caddy rollback edge and shared Nginx/Certbot model, rejects mutable/default release configuration, checks network/resource boundaries, and statically rejects global cleanup or schema-downgrade commands. It does not connect to or mutate the production host.

## Repository safety

The local `est-test/` export, `est-test.tar.gz`, media, environment files, Telegram sessions, local databases, and generated sensitive reports must never be committed or copied into Docker build contexts.

Use `.env.example` only as a list of names and non-runnable placeholders. Complete production configuration is transferred from GitHub Actions during deployment and is never committed.

## Contribution workflow

Each implementation task requires:

1. an approved epic spike;
2. promotion from `proposed-tasks/` to `tasks/`;
3. an approved implementation plan;
4. completed dependencies, or recorded ordered ancestry under the approved stacked-PR gate; and
5. one dedicated branch and pull request.

GitHub-enforced branch protection is currently out of scope, so reviews and checks are enforced procedurally.
