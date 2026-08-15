# Warsaw Estate Platform

Warsaw Estate Platform (WEF) will turn a Telegram real-estate export into a filterable map of Warsaw developments and offers.

## Current status

The repository contains a browser-visible synthetic M1: a forward-migrated PostGIS catalog, backend-authoritative grouped GeoJSON/facets/dated results, and a responsive MapLibre/OpenFreeMap map with an accessible companion list. Historical ingestion, URL-backed filters, authentication, real media/data, and deployment remain task-gated follow-up work.

Start with:

- [AI documentation index](AI/README.md)
- [Architecture](AI/architecture/README.md)
- [E0 proof report](AI/epics/E0-architecture-dependency-spike/PROOF_REPORT.md)
- [Epics and task dependencies](AI/epics/README.md)
- [Approval-gated workflow](AI/workflow/README.md)
- [Repository and change rules](AI/governance/REPOSITORY_RULES.md)

## Planned stack

- Python, FastAPI, SQLAlchemy, PostgreSQL, and PostGIS
- TypeScript, Next.js, React, and MapLibre
- Docker Compose; Caddy for the current local/interim stack and Nginx plus Certbot/Let's Encrypt for the target shared production edge
- GitHub Actions and GitHub Container Registry

The backend is authoritative for business behavior. The frontend primarily renders generated API contracts and backend-provided projections.

## Architecture proof

Prerequisites are Python 3.13.2, Node.js 22.22.2, uv, Corepack/pnpm, and Docker. Versions are recorded in `.tool-versions` and lockfiles.

```shell
make install
make format-check lint typecheck test contract-check
make build
```

`make test` automatically uses `TEST_DATABASE_URL` from the environment and
fails immediately with a configuration error when it is missing. The URL must
point to a disposable PostGIS database; CI configures one for every run. Static
API documentation is generated as an artifact and is not served by the
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

This describes the current local/rehearsal implementation. [ADR-020](AI/decisions/adr/ADR-020-use-nginx-shared-tls-ingress.md) selects Nginx as the target NUC web server, with free Certbot renewal for both WEF and the existing AI Forecast service. [E7-T8](AI/epics/E7-production-delivery/tasks/E7-T8-build-shared-nginx-tls-ingress.md) and [E7-T9](AI/epics/E7-production-delivery/tasks/E7-T9-implement-reversible-shared-edge-cutover.md) build inert topology/automation; [E7-T10](AI/epics/E7-production-delivery/proposed-tasks/E7-T10-roll-out-and-verify-shared-tls.md) remains gated before live activation.

`make up` applies forward Alembic migrations before API startup. `make seed-m1` explicitly converges a small invented Warsaw fixture for map/API verification; production requires a separate explicit rehearsal opt-in and the command never reads the local export.

Open `http://127.0.0.1:3100/` after seeding. The public map style defaults to keyless OpenFreeMap and can be replaced at image-build time with `NEXT_PUBLIC_MAP_STYLE_URL`; OpenFreeMap/OpenStreetMap attribution remains visible in the map shell.

`make importer-dry-run` starts the operator profile, confirms that
`WEF_SOURCE_DIR` is mounted read-only, streams the configured historical export
through the rule-bound E2 parser, and atomically writes detailed JSON/Markdown
reports plus privacy-safe aggregate audit evidence below the configured ignored
report destination. It prints only terminal status/counts and performs no
database/geocode/media write, media copy, or network request.

The inert production model is separate from local Compose:

```shell
make production-proof
```

That command renders the digest-only `wef-production` topology, validates Caddy, rejects mutable/default release configuration, checks internal networks/single-edge-port/resource boundaries, and statically rejects global cleanup or schema-downgrade commands. It does not connect to or mutate the production host.

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
