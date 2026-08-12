# Warsaw Estate Platform

Warsaw Estate Platform (WEF) will turn a Telegram real-estate export into a filterable map of Warsaw developments and offers.

## Current status

The repository contains a forward-migrated synthetic M1 PostGIS catalog and backend-authoritative grouped GeoJSON map query, plus committed/generated API contracts, tests, non-root application images, persistent development volumes, and a same-origin Caddy edge. It is not yet the browser MVP: MapLibre rendering, contextual facets/results, historical ingestion, authentication, and deployment remain task-gated follow-up work.

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
- Docker Compose with Caddy
- GitHub Actions and GitHub Container Registry

The backend is authoritative for business behavior. The frontend primarily renders generated API contracts and backend-provided projections.

## Architecture proof

Prerequisites are Python 3.13.2, Node.js 22.22.2, uv, Corepack/pnpm, and Docker. Versions are recorded in `.tool-versions` and lockfiles.

```shell
make install
make format-check lint typecheck test contract-check
make build
```

The real PostGIS test runs only with an explicit disposable `TEST_DATABASE_URL`. Static API documentation is generated as an artifact and is not served by the production API.

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

`make up` applies forward Alembic migrations before API startup. `make seed-m1` explicitly converges a small invented Warsaw fixture for map/API verification; the command refuses `WEF_ENV=production` and never reads the local export.

`make importer-dry-run` starts the operator profile and confirms that `WEF_SOURCE_DIR` is mounted read-only. It reports only a file count and does not read file contents, parse listings, contact Telegram, or persist imports.

## Repository safety

The local `est-test/` export, `est-test.tar.gz`, media, environment files, Telegram sessions, local databases, and generated sensitive reports must never be committed or copied into Docker build contexts.

Use `.env.example` only as a list of safe local-development names. Production configuration is transferred from GitHub Actions during deployment and is never committed.

## Contribution workflow

Each implementation task requires:

1. an approved epic spike;
2. promotion from `proposed-tasks/` to `tasks/`;
3. an approved implementation plan;
4. completed dependencies, or recorded ordered ancestry under the approved stacked-PR gate; and
5. one dedicated branch and pull request.

GitHub-enforced branch protection is currently out of scope, so reviews and checks are enforced procedurally.
