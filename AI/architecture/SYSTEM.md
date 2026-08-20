# Architecture

## Architecture goals

- Deliver the complete MVP on one modest Linux server for fewer than 10,000 users.
- Keep domain decisions, authorization, filtering, grouping, masking, and display projections authoritative in the backend; the frontend primarily renders and localizes returned data.
- Keep parsing, geocoding, and Telegram source logic outside request handlers.
- Make every historical and live ingestion operation replayable and traceable.
- Keep map, geocoder, media, and hosting providers replaceable.
- Apply SOLID/DRY with explicit boundaries, interactors, presenters, domain/application services, ports, and adapters without generic framework abstractions.
- Scale vertically first and add infrastructure only when measured limits justify it.

## System context

```mermaid
flowchart LR
    visitor[VisitorBrowser]
    maintainer[Maintainer]
    github[GitHubActions]
    telegram[Telegram]
    geocoder[GeocodingProvider]
    tiles[OpenFreeMap]

    subgraph server [Single Docker Host]
        nginx[Nginx TLS ingress]
        certbot[Certbot ACME renewal]
        web[NextWeb]
        api[FastAPI]
        worker[ImporterTelegramWorker]
        db[(PostgreSQLPostGIS)]
        media[(MediaVolume)]
        forecast[Existing AI Forecast]
    end

    visitor -->|"HTTPS 80/443 after E7-T10"| nginx
    visitor -->|"Vector tiles"| tiles
    nginx --> web
    nginx --> api
    nginx --> media
    nginx --> forecast
    certbot -.->|"Certificates and renewal reload"| nginx
    api --> db
    worker --> db
    worker --> media
    worker --> geocoder
    telegram --> worker
    maintainer -->|"HTTPS owner admin"| nginx
    maintainer -->|"Import command and review reports"| worker
    github -->|"Immutable images over SSH deploy"| server
```

OpenFreeMap and the geocoder are external dependencies, not containers owned by this project. All project-owned runtime processes are containerized. The implemented anonymous rehearsal still uses Caddy on port 3100. [E7-T8](../epics/E7-production-delivery/tasks/E7-T8-build-shared-nginx-tls-ingress.md) owns inert shared-edge topology, [E7-T9](../epics/E7-production-delivery/tasks/E7-T9-implement-reversible-shared-edge-cutover.md) owns cutover automation, and [E7-T10](../epics/E7-production-delivery/tasks/E7-T10-roll-out-and-verify-shared-tls.md) owns the live Nginx/Certbot migration; [E7-T7](../epics/E7-production-delivery/proposed-tasks/E7-T7-enable-production-registration-and-contact-reveal.md) enables sensitive WEF behavior only after that HTTPS gate.

## Technology stack

### Web application

- TypeScript in strict mode.
- Next.js App Router and React.
- MapLibre GL JS through the MapLibre entry point provided by `react-map-gl`.
- TanStack Query for server-state fetching, cancellation, caching, and error handling.
- `openapi-typescript` and `openapi-fetch` for generated API contracts rather than handwritten domain/API types.
- `next-intl` with English keys for interface copy and locale-aware display formatting.
- URL search parameters as the source of truth for user-selected filters.
- Tailwind CSS with accessible Radix primitives and selectively generated shadcn components.
- Zod/React Hook Form for immediate form usability; backend validation remains authoritative.

Avoid a global client-state library initially. Local component state, URL state, and TanStack Query cover the MVP.

The map is a client component loaded only in the browser. The route shell, metadata, and accessible non-map structure can render on the server.

### API and ingestion

- Python with type checking enabled.
- FastAPI and Pydantic for validated HTTP contracts and OpenAPI.
- FastAPI Users with SQLAlchemy as an evaluated foundation for username/password registration and database-backed cookie sessions; the spike replaces it if adapting email-oriented defaults is not worthwhile.
- Starlette Admin for the HTTPS-only owner console, with project-owned auth, CSRF, permissions, interactors, and audit.
- SQLAlchemy 2 for persistence and explicit transactions.
- Alembic for forward-only schema migrations.
- `asyncpg` as the PostgreSQL driver.
- `ijson` for streaming the historical export rather than loading the whole document into memory.
- `httpx` for controlled external HTTP calls.
- Telethon in the future long-running Telegram worker.
- Structlog configured for structured JSON in production.

Durable imports, media work, and Telegram updates do not run as FastAPI background tasks. They use a separate process/container so API restarts do not lose jobs.

### Data and edge

- PostgreSQL with PostGIS for spatial predicates and indexes.
- Nginx for target public TLS, routing, compression, security headers, and local media delivery; Certbot for free Let's Encrypt issuance/renewal. Caddy remains only in the implemented interim rehearsal until E7-T10.
- A mounted media volume for the MVP.
- OpenFreeMap vector styles/tiles, configured through environment values.

Redis, a task queue, Elasticsearch, Kubernetes, and a service mesh are intentionally absent.

## Planned repository shape

```text
AI/
  README.md
  product/
    README.md
    SCOPE.md
    EXPERIENCE.md
    QUALITY.md
  data/
    README.md
    SOURCE_BASELINE.md
    QUALITY_AND_READINESS.md
  contracts/
    README.md
    DATA_MODEL.md
    HTTP_API.md
    OPENAPI.md
  architecture/
    README.md
    SYSTEM.md
    DEPENDENCY_BASELINE.md
  ingestion/
    README.md
    PIPELINE.md
    GEOCODING.md
  security/
    README.md
    AUTH_ADMIN_CONTACTS.md
  operations/
    README.md
    DEPLOYMENT.md
    SERVER.md
  governance/
    README.md
    REPOSITORY_RULES.md
  decisions/
    README.md
    adr/
    deferred/
  milestones/
    README.md
  epics/
    README.md
    E*-*/
      README.md
      SPIKE.md
      IMPLEMENTATION_PLAN.md
      proposed-tasks/
      tasks/                 # created only by valid task promotion
  workflow/
    README.md
    DEFINITION_OF_DONE.md
    templates/
contracts/
  openapi/
    v1.json
apps/
  web/
    tests/
  backend/
    src/wef/
      bootstrap/
      shared/
      catalog/
        domain/
        application/
        infrastructure/
        interface/
      ingestion/
      identity/
      administration/
      contact_reveal/
    migrations/
    tests/
      unit/
      integration/
      contract/
      architecture/
infra/
  compose.yaml
  compose.production.yaml
  Caddyfile.production  # implemented interim WEF edge
  nginx/                # target shared-edge configuration from E7-T8
tests/
  fixtures/  # shared synthetic/redacted cross-application fixtures only
.github/
  workflows/
```

Backend code is a package-by-feature modular monolith. Each feature follows the inward dependency rule `interface -> application -> domain`; infrastructure implements inward-owned ports and is wired only in the composition root. `import-linter` enforces layer, feature-independence, forbidden-import, and acyclic contracts.

Interactors own use-case orchestration and mutation transaction boundaries. Query services own backend-computed read projections. Domain/application services hold reusable rules. Presenters map application output DTOs to versioned Pydantic responses and perform no I/O or authorization. Route handlers remain transport adapters and do not contain business logic.

The API, historical importer, and Telegram listener share feature/domain/application modules but start with different commands from the same backend image. Detailed boundaries, dependencies, examples, and the required proof are in the [Epic 0 architecture/dependency spike](../epics/E0-architecture-dependency-spike/SPIKE.md).

## Runtime components

### Nginx and Certbot

- Nginx is the target public web server and TLS reverse proxy on ports 80/443; the implemented Caddy edge continues serving the bounded anonymous WEF rehearsal on configurable port 3100 until E7-T10 cutover.
- Uses separate hostnames to route WEF and the existing AI Forecast frontend currently exposed on port 3000.
- Certbot obtains free Let's Encrypt certificates, persists its complete state, renews unattended, and gracefully reloads Nginx only after successful renewal.
- Routes `/api/*` to FastAPI.
- Routes application requests to Next.js.
- Serves `/media/*` from a read-only volume using generated storage keys.
- Adds conservative security headers.
- Exposes no application, database, or worker upstream port publicly after cutover.
- Keeps shared-ingress deploy/rollback independent of ordinary WEF application releases.

### Next.js web

- Delivers the route shell and frontend assets.
- Calls the same-origin `/api/v1` endpoints.
- Renders/localizes backend-computed projections and capabilities; it does not duplicate filter, grouping, visibility, masking, source-link, or authorization rules.
- Requests vector tiles directly from the configured style provider.
- Does not receive database credentials, storage paths, Telegram credentials, or private geocoder keys.
- Treats every `NEXT_PUBLIC_*` value as public by definition.

### FastAPI

- Provides public, read-only map/filter/detail endpoints.
- Provides same-origin account/session endpoints and the authenticated contact-reveal mutation.
- Validates query ranges, bounding boxes, and pagination.
- Routes invoke one application query/interactor and present its output; routes do not contain domain logic or persistence.
- Returns compact location summaries for maps and separate detail payloads.
- Generates OpenAPI used to verify or generate frontend types.
- Exposes liveness and readiness endpoints.
- Does not parse raw Telegram exports or download media inside web requests.
- Masks contacts in every anonymous response; plaintext contact decryption exists only in the authorized no-store reveal path.
- Generates the canonical OpenAPI contract offline, while production disables `openapi_url`, Swagger UI, and ReDoc routes.

The committed schema, frontend generation, static Redocly CI artifact, breaking-change checks, and production 404 requirements are defined in the [OpenAPI contract](../contracts/OPENAPI.md).

### Owner admin console

- Starlette Admin renders owner-only server-side pages under `/admin` after HTTPS.
- Its custom authentication provider delegates to the identity application service.
- User/session/password-reset/reveal-audit actions call owner-authorized interactors and write `AdminAuditEvent`; model views do not write sensitive tables directly.
- Admin HTML/actions are outside public OpenAPI and require explicit secure-cookie, CSRF/origin, rate-limit, no-store, and authorization tests.

### Importer/Telegram worker

- Runs one-off `import dry-run`, `import historical`, `import reprocess`, and `import verify-media` commands.
- Later runs a single long-lived Telegram listener.
- Acquires a PostgreSQL advisory lock per channel/import mode to prevent duplicate concurrent processors.
- Persists checkpoints and ingestion runs.
- Uses bounded concurrency for media and provider calls.
- Exits non-zero on an incomplete one-off run.

### PostgreSQL/PostGIS

- Is the canonical source for public application data.
- Uses normal relational fields for filterable values and PostGIS points for locations.
- Uses a GiST spatial index plus selective B-tree indexes defined in the [data model](../contracts/DATA_MODEL.md).
- Is reachable only on the Compose network.

### Media storage

- The storage interface accepts a stream and returns an opaque key, checksum, byte count, detected MIME type, and dimensions/duration where available.
- The local implementation writes atomically to a mounted volume.
- Database rows store keys such as checksum-derived paths, never absolute host paths.
- The active edge receives the same volume read-only: Caddy during the interim rehearsal and Nginx after E7-T10.
- A future S3 implementation can preserve public API URL semantics.

## Main request flow

1. The browser opens a page through the active same-origin edge: interim Caddy or target Nginx.
2. Next.js returns the route shell; the client-only map initializes MapLibre.
3. MapLibre loads the configured OpenFreeMap style and tiles with required attribution.
4. The client parses filters from the URL and requests `/api/v1/map/locations` with the viewport bounding box.
5. FastAPI validates the request, executes spatial/filter queries, and returns compact GeoJSON.
6. MapLibre clusters and renders points client-side.
7. Selecting a point requests `/api/v1/locations/{id}` for related offers.
8. Media loads from same-origin opaque `/media/` URLs.

For the expected few hundred locations, client-side MapLibre clustering is simpler and sufficient. Server-side tile generation is a later scale option, not an MVP requirement.

## Ingestion flow

```mermaid
flowchart LR
    adapter[SourceAdapter] --> raw[RawMessage]
    raw --> detect[CandidateDetection]
    detect --> extract[FieldExtraction]
    extract --> normalize[Normalization]
    normalize --> dedupe[IdentityAndDedup]
    dedupe --> locate[GeocodeAndValidate]
    locate --> persist[TransactionalPersistence]
    raw --> group[MediaGrouping]
    group --> store[MediaStorage]
    store --> persist
    persist --> report[ImportReport]
```

Source adapters are replaceable. Every stage records parser/rule versions and reason codes so a new parser can reprocess saved raw messages without redownloading Telegram history.

## Configuration

Configuration is validated at process startup.

Categories include:

- Public: site URL, map style URL, default center/bounds, displayed attribution.
- Shared private: database URL and media root.
- Auth private: public/admin session secrets, contact encryption/HMAC keys, allowed origin, and one-time owner bootstrap credentials.
- Import private: geocoder credentials/contact identity and source paths.
- Telegram private: API ID, API hash, session string, and configured channel entity.
- Deployment private: registry pull credentials and SSH deployment material.

GitHub Actions variables/secrets are the deployment source of truth. Every deployment transfers a complete configuration to an atomic mode-0600 release directory on the server; no value is committed or printed, and no default secret is accepted in production.

## Reliability and observability

- `/api/v1/health/live` confirms the API process is running.
- `/api/v1/health/ready` checks required database connectivity and migration compatibility.
- Compose health checks gate dependent services.
- Logs include timestamp, level, service, environment, release SHA, request/run ID, and event name.
- API access logs exclude query values that could contain source text or contact data.
- Import metrics are persisted in `ingest_runs` and its report artifact.
- External calls use explicit connect/read timeouts, bounded retries with jitter, and provider-specific rate limits.
- An external uptime check is recommended after the server is supplied.

No dedicated metrics stack is required initially. Add one when logs and host-level monitoring cannot answer operational questions.

## Security boundaries

- Only SSH and the configured WEF edge port are public for the interim deployment; after TLS migration the intended public application ports are 80/443.
- PostgreSQL and worker processes have no public ports.
- Containers run as non-root where their base image permits.
- Images use pinned runtime versions, minimal production stages, and read-only filesystems where practical.
- Uploaded/source media is not executable and is served with detected content types plus `X-Content-Type-Options: nosniff`.
- API query values are parameterized through SQLAlchemy.
- CORS is unnecessary when the web and API are same-origin.
- Rate limiting belongs at the active edge—target Nginx after E7-T10—for abusive public traffic; initial limits should be measured to avoid breaking map use.

## Test strategy

- Backend unit tests: parser rules, normalization, deduplication, filter semantics, and link construction with pytest.
- Backend integration tests: PostgreSQL/PostGIS queries and migrations against an ephemeral container.
- Architecture tests: `import-linter` enforces inward layers, feature independence, forbidden framework imports, and acyclic modules.
- Application tests invoke interactors/query services with fakes at narrow ports; presenter tests verify serialization independently.
- Frontend unit/component tests: filter serialization, result states, and accessible controls with Vitest and Testing Library.
- End-to-end tests: map/list/detail critical path with Playwright using deterministic API fixtures.
- Contract check: generated OpenAPI must match checked/generated TypeScript client types.
- Import golden tests: synthetic Telegram fixtures produce versioned expected records and reconciled counts.

## Scale boundaries and triggers

Remain on this topology while:

- The database and media fit comfortably on one host with disk headroom.
- API latency meets the target.
- A deploy restart is acceptable.
- The Telegram worker can keep pace with one channel.

Revisit architecture when measured conditions show:

- Map payloads become large enough to require server-side vector tiles.
- Database reads need a replica or connection pooler.
- Media bandwidth or disk pressure favors object storage and a CDN.
- Multiple ingestion channels or expensive jobs require a durable queue.
- Availability requirements justify at least two application hosts.

These are triggers, not pre-approved dependencies.
