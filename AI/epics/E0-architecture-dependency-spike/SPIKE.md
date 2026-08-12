---
schema: ai-workflow/spike@1
epic: E0
title: "Backend-centric architecture and dependencies"
status: approved
revision: 2
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-001, ADR-005, ADR-012, ADR-013, ADR-016, ADR-017]
domain_docs: [architecture, contracts, governance, security]
proposed_task_ids: [E0-T1, E0-T2]
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-12T21:03:00Z"
  approved_revision: 2
  evidence: "Explicit owner approval in the current Cursor conversation: E0 spike revision 2"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Backend-Centric Architecture and Dependencies

## Status

- Type: architecture/dependency spike.
- Priority: P0, first architecture/dependency research activity; only repository safety/bootstrap may precede the proposed post-approval implementation proof.
- Proposed E0-T2 branch: `spike/backend-architecture-dependencies`; this research artifact does not authorize creating or using it.
- Research output: recommended architecture boundaries, dependency responsibilities, and a proposed contract-proof scope. Manifests, lockfiles, and proof code remain future implementation outputs.
- Gate: spike revision 2 and implementation-plan revision 3 are owner-approved. Promoted tasks may proceed only through their own state, dependency, branch, review, and completion gates.

## Question

How should WEF keep business behavior in the backend, make the frontend primarily represent server data, and apply SOLID/DRY with explicit interactors, presenters, domain services, and infrastructure adapters without over-engineering a sub-10k-user system?

## Conclusion

Build a backend-centric modular monolith:

- One FastAPI application image plus importer/Telegram commands from the same Python codebase.
- Feature modules with domain, application, infrastructure, and interface boundaries.
- Interactors own use-case orchestration and transaction boundaries.
- Domain services/service objects own reusable business rules that do not naturally belong to one entity/value object.
- Read query services produce backend-computed map/list/detail projections.
- Presenters convert application outputs into stable versioned API response schemas.
- Repositories and external-service ports are defined inward and implemented by infrastructure adapters.
- Next.js renders, localizes, and coordinates UI state. It does not reimplement domain rules.
- PostgreSQL/PostGIS remains the source of truth; no microservices, message broker, Redis, or generic enterprise framework for the MVP.

SOLID and DRY are constraints on changeability, not a reason to add abstractions before there are separate responsibilities or implementations.

## Architecture principles

### Backend is authoritative

The backend exclusively owns:

- Offer/location visibility.
- Filter, range-overlap, sorting, pagination, and facet semantics.
- Map grouping/clustering inputs and matching-offer counts.
- Publication/status wording codes and unsupported-availability prevention.
- Source lineage, duplicate handling, and canonicalization.
- Contact extraction, encryption, masking, authorization, reveal rate limits, and audit.
- Telegram URL construction and verification.
- Media ordering, safe URLs, and missing-media behavior.
- Geocoding acceptance, Warsaw bounds, precision, and review states.
- Authentication, sessions, permissions, and restricted-action decisions.
- Import idempotency, reconciliation, transaction boundaries, and checkpoints.

The API returns display-ready projections with normalized values, explicit nullability, stable enum/error codes, links, permissions/capabilities, and pagination metadata.

### Frontend is intentionally thin

The frontend owns only presentation concerns:

- Layout, responsive behavior, map interaction, focus, and accessibility.
- English translation lookup through i18n keys.
- Locale-aware number/date formatting from normalized backend values.
- URL/search parameter editing for filter controls.
- Request lifecycle, loading/empty/error states, and short-lived server-state caching.
- Explicit user gestures such as contact reveal.

The frontend must not:

- Recalculate whether an offer matches a filter.
- Join or group offers/locations.
- Infer availability, visibility, permissions, or geocoding confidence.
- Build Telegram/media URLs from IDs.
- Mask or authorize contact data.
- Duplicate backend enums with handwritten TypeScript types.
- Persist revealed contacts.
- Contain a second domain/service layer.

Generated OpenAPI types plus `openapi-fetch` are the only normal API contract source. Frontend validation exists for immediate form usability; FastAPI remains authoritative.

## SOLID and DRY rules

### Single responsibility

- One interactor represents one user/system action.
- One presenter represents one API response family.
- A repository handles persistence for a defined aggregate/query contract, not arbitrary application behavior.
- A provider adapter handles one external system boundary.
- Route handlers parse transport input, invoke one interactor/query, and select a presenter.

### Open/closed and dependency inversion

- Geocoder, media storage, Telegram, clock, ID generation, encryption, and persistence are ports.
- New providers implement ports without changing domain/application behavior.
- Application/domain code never imports FastAPI, SQLAlchemy models, Caddy, Telethon, provider SDKs, or filesystem paths.

### Interface segregation and substitution

- Prefer narrow ports such as `OfferReadRepository`, `OfferWriteRepository`, `Geocoder`, `ContactCipher`, and `UnitOfWork`.
- Do not create one repository/provider interface containing every operation.
- When a port has multiple implementations, shared contract tests prove that each implementation honors the same behavior. A single adapter needs focused integration tests but does not justify a generic contract-test harness by itself.

### DRY

- A business rule has one backend implementation and one test suite.
- Shared code is extracted only after a stable concept or repeated rule exists.
- Similar-looking transport/ORM/domain models remain separate when they have different reasons to change.
- Do not use generic `BaseRepository`, `BaseService`, universal CRUD, or reflection-heavy mapping to remove harmless explicit code.

## Backend modular monolith

### Dependency direction

```text
interface/http or interface/cli
              |
              v
application/interactors + application/queries + ports
              |
              v
domain/entities + value_objects + policies + services

infrastructure/adapters ---> application ports
bootstrap/composition  ---> wires interface, application, and infrastructure
```

Allowed:

- Interface imports application contracts and response schemas.
- Application imports domain and its own ports.
- Domain imports Python standard library and narrowly approved value libraries only.
- Infrastructure imports application ports/domain types and vendor libraries.
- Bootstrap imports every layer only to construct dependencies.

Forbidden:

- Domain importing application, infrastructure, FastAPI, Pydantic, or SQLAlchemy.
- Application importing concrete repositories/adapters or HTTP request/response types.
- Interactors returning ORM models.
- Presenters querying a repository or invoking external services.
- Repositories committing transactions.
- Feature modules importing another feature's infrastructure.

`import-linter` exhaustive layer, independence, forbidden-import, and acyclic-sibling contracts enforce these rules in CI.

### Package by feature

```text
apps/backend/
  pyproject.toml
  src/wef/
    bootstrap/
      api.py
      cli.py
      container.py
      settings.py
    shared/
      domain/
      application/
      infrastructure/
      interface/
    catalog/
      domain/
        entities.py
        value_objects.py
        policies.py
        services.py
      application/
        commands.py
        queries.py
        interactors/
        query_services/
        ports/
        dto.py
      infrastructure/
        sqlalchemy/
        repositories/
        geocoding/
        media/
      interface/
        http/
          routes.py
          schemas.py
          presenters.py
    ingestion/
      domain/
      application/
      infrastructure/
      interface/cli/
    identity/
      domain/
      application/
      infrastructure/
      interface/http/
    administration/
      application/
      infrastructure/
      interface/admin/
    contact_reveal/
      domain/
      application/
      infrastructure/
      interface/http/
  migrations/
  tests/
    unit/
    integration/
    contract/
    architecture/
```

Feature packages are independent by default. Shared abstractions move to `shared` only when at least two modules use the same stable concept.

### Entities and value objects

- Entities contain identity and invariant-preserving behavior.
- Immutable value objects represent money/ranges, areas, coordinates/bounds, publication timestamps, source identity, confidence, masked contacts, and pagination cursors.
- Domain constructors reject invalid state.
- Domain objects are separate from SQLAlchemy and Pydantic classes.
- Avoid anemic entities when a rule belongs naturally to the entity, but do not force query/projection behavior into aggregates.

### Interactors

Interactors are application use cases, named as actions:

- `ListMapLocations`.
- `ListLocationOffers`.
- `GetOfferDetail`.
- `RevealOfferContacts`.
- `RegisterUser`.
- `DisableUser`.
- `RevokeUserSessions`.
- `ForceResetUserPassword`.
- `ListContactRevealAudit`.
- `ImportHistoricalMessages`.
- `ProcessSourceMessage`.
- `ReprocessSourceMessages`.

An interactor:

1. Receives an application input DTO plus an actor/context.
2. Loads through narrow repositories/queries.
3. Applies domain policies/services.
4. Coordinates adapters.
5. Commits through a `UnitOfWork` when mutating.
6. Returns an application output DTO or typed application error.

It does not know FastAPI request objects, status codes, cookies, SQLAlchemy sessions, or JSON shapes.

### Query services and CQRS-lite

Map/filter/detail reads are projection-heavy and should not hydrate full aggregates unnecessarily.

- Application query interfaces describe backend-owned read behavior.
- SQLAlchemy/PostGIS query-service adapters execute optimized joins, spatial predicates, facets, sorting, and cursor pagination.
- Query results are immutable application read DTOs.
- Commands/interactors still use aggregates/repositories where invariants and writes matter.
- This is CQRS-lite inside one process/database, not separate services or event-sourced storage.

### Domain services/service objects

Use a domain service when a pure business rule spans multiple entities/value objects:

- `OfferFilterPolicy`.
- `LocationAcceptancePolicy`.
- `CanonicalOfferMatcher`.
- `ContactMaskingPolicy`.
- `SourceLinkPolicy`.

Use an application service when orchestration is reused by multiple interactors but is not itself a user action:

- `MediaIngestionService`.
- `GeocodingWorkflow`.
- `SourceNormalizationService`.

Rules:

- Prefer stateless, deterministic services.
- Make I/O explicit through injected ports.
- Avoid `SomethingManager`, generic service registries, and services that become alternate application layers.

### Presenters

Presenters live at the delivery boundary and map application outputs to versioned Pydantic response schemas.

Examples:

- `MapLocationsPresenter`.
- `OfferDetailPresenter`.
- `ProblemDetailsPresenter`.
- `ContactRevealPresenter`.

Presenters own:

- API field naming and response envelope shape.
- Stable enum/error code serialization.
- Link and capability placement already authorized by the application result.
- Decimal/date/geometry serialization.
- Public omission/null rules.

Presenters do not:

- Query data.
- Apply authorization or business filtering.
- Decrypt or mask contacts.
- Localize UI prose.
- Mutate domain/application state.

Errors use one RFC 9457-style problem response contract with stable machine-readable codes. The frontend maps codes to i18n keys.

### Routes and controllers

FastAPI route functions remain small:

1. Validate transport shape with Pydantic.
2. Resolve authenticated/anonymous actor and dependencies.
3. Build the interactor/query input.
4. Invoke one application entry point.
5. Present success or map typed errors.

Pydantic validators validate shape/format only; they do not query the database or contain domain decisions.

### Persistence and transactions

- SQLAlchemy mappings are infrastructure-only.
- Repositories `flush` when identifiers are needed but never `commit`.
- A unit of work owns one mutation transaction per interactor/import batch.
- Read query services use explicit sessions and no hidden writes.
- Import batches are bounded, restartable, idempotent, and checkpoint only after commit.
- External calls normally happen before a short database write transaction; unavoidable cross-system workflows record resumable state.
- Alembic migrations are forward-first and reviewed independently from ORM changes.

### Dependency injection

Use explicit constructors plus a small composition root and FastAPI's request dependency mechanism.

Do not add a third-party DI container initially. Reconsider only if manual wiring becomes a measured maintenance problem.

### Internal events

Use direct calls by default. Small in-process domain/application events are allowed for decoupled post-commit effects, but:

- No event broker for MVP.
- Event handlers must be explicit and tested.
- Critical persistence cannot rely on best-effort background tasks.
- Import work that must survive restart uses persisted state and a dedicated process.

## Frontend architecture

```text
apps/web/src/
  app/
  features/
    map/
    offers/
    auth/
    contact-reveal/
  components/
  lib/
    api/
      generated/
      client.ts
      query-options.ts
    i18n/
  messages/
    en.json
```

- `openapi-typescript` generates API types from the committed FastAPI schema.
- `openapi-fetch` is the typed transport.
- TanStack Query owns remote request/cache lifecycle; query keys/options are centralized.
- URL parameters own public filter state.
- Local React state owns transient visual state.
- `next-intl` owns English keys and locale-aware display formatting.
- Zod/React Hook Form provide immediate form feedback only; server errors remain authoritative.
- No Redux/Zustand/domain store initially.
- No Next.js API routes duplicate FastAPI business behavior. A narrow proxy is allowed only for same-origin/cookie infrastructure if deployment requires it.
- Server Components may fetch read data; the map and interactive controls remain client components.

## Request flows

### Read flow

```text
Browser
  -> FastAPI route
  -> ListMapLocations query
  -> PostGIS query-service adapter
  -> application read DTO
  -> MapLocationsPresenter
  -> OpenAPI response
  -> generated TypeScript client
  -> thin React/MapLibre rendering
```

### Contact reveal flow

```text
Explicit browser click
  -> authenticated FastAPI route + CSRF/origin checks
  -> RevealOfferContacts interactor
  -> user/offer policy + rate-limit query
  -> contact repository + cipher port
  -> audit write + unit-of-work commit
  -> no-store application output
  -> ContactRevealPresenter
  -> transient frontend rendering
```

### Ingestion flow

```text
Historical JSON or Telegram adapter
  -> source input DTO
  -> ProcessSourceMessage interactor
  -> normalization/domain services
  -> geocoder/media ports
  -> repositories + unit of work
  -> ingest report presenter
```

## Proposed dependency inventory

Exact versions would be pinned only in future committed lockfiles and updated by reviewed automation. This research selects responsibilities, not unverified version numbers.

Category labels are deliberate:

- **Adopt** means the dependency responsibility is accepted; E0-T2 still verifies version, license, compatibility, and advisories.
- **Evaluate in E0-T2** means both the candidate and its stated project-owned or simpler fallback are acceptable until measured proof selects one.
- **Defer** means the dependency is accepted only for a later approved epic and is absent from the vertical-proof runtime.
- **Reject for MVP** means the dependency is excluded and the stated accepted stack/project-owned replacement is used instead.

Current documentation checks on 2026-08-12:

- OpenAPI TypeScript documents schema-to-TypeScript generation and typed `openapi-fetch` clients, including Next.js server-side use.
- `next-intl` documents English/static App Router configuration, Server/Client Component providers, and centralized number/date formats.
- Import Linter documents exhaustive layered, independence, forbidden, protected, and acyclic contracts.
- FastAPI Users v15.0.5 was active when researched and documents SQLAlchemy integration, Argon2/pwdlib, cookie transport, and database token strategy; proposed E0-T2 acceptance must determine whether adapting its email-oriented defaults to username-only auth is worthwhile after approval.
- Starlette Admin 0.17.1 was current/active when researched and documents SQLAlchemy integration, custom auth providers, per-view permissions, and custom actions; project-owned CSRF/session hardening remains mandatory.
- Current official Docker documentation confirms named multi-stage Dockerfile stages, strict `.dockerignore`-controlled build contexts, digest-pin policies, and BuildKit secret/cache mounts rather than persistent credentials in `ARG`, `ENV`, or image layers.
- Current Compose v2 documentation confirms long-syntax read-only mounts, named volumes, health checks with `depends_on.condition: service_healthy`, optional profiles, and project-name isolation without explicit `container_name` values.

### Backend production: adopt unless marked evaluate/defer

- Python: current stable supported line would be selected/pinned during approved E0-T2 implementation.
- `fastapi`: HTTP routing, dependency hooks, OpenAPI.
- `uvicorn[standard]`: ASGI process for MVP.
- `pydantic` and `pydantic-settings`: transport schemas and configuration.
- `sqlalchemy[asyncio]`: ORM mappings, queries, explicit transactions.
- `asyncpg`: PostgreSQL async driver.
- `alembic`: schema migrations.
- `geoalchemy2`: PostGIS type/function integration.
- **Evaluate in E0-T2:** `fastapi-users[sqlalchemy]` as a username/password/session foundation behind the identity module; replace it with focused project-owned identity/session code if adapting email-oriented defaults is more complex or less secure.
- `pwdlib[argon2]`: password hashing through the auth integration.
- `starlette-admin`: owner-only server-rendered user/session/reset/reveal-audit console.
- `cryptography`: authenticated contact encryption/key rotation primitives.
- `httpx`: geocoder, link resolver, and provider HTTP adapters.
- `ijson`: bounded historical-export streaming.
- `typer`: explicit importer/operator CLI.
- `structlog`: structured event logging without source/contact payloads.
- `phonenumbers`: phone recognition/normalization/masking support; project policy decides what is revealable.
- `pillow`: image metadata and derivatives.
- **Defer to Epic 8:** `telethon` for the future Telegram adapter; historical/synthetic ingestion does not install or import it.

### Backend test/quality: adopt unless marked evaluate

- `pytest`.
- `pytest-asyncio`.
- `httpx` test client support.
- **Evaluate in E0-T2:** `testcontainers[postgres]` versus a CI PostGIS service for real integration tests; use the service directly if Docker-in-Docker is unreliable.
- **Evaluate in E0-T2:** `factory-boy` versus lightweight project factories; use project factories when the dependency does not remove meaningful fixture complexity.
- `hypothesis` for parser/range/value-object properties where it adds coverage.
- `ruff` for formatting and linting.
- `mypy` in strict mode for project code.
- `import-linter` for enforced architecture contracts.
- `coverage` with branch coverage.
- `pip-audit` for Python dependency advisories.

### Frontend production: adopt unless marked evaluate

- `next`, `react`, `react-dom`.
- `typescript` strict mode.
- `maplibre-gl`.
- `react-map-gl` using its MapLibre entry point.
- `@tanstack/react-query`.
- `openapi-fetch`.
- `next-intl`.
- **Evaluate in E0-T2:** `nuqs` for typed URL filter state; omit it and use direct `URLSearchParams` if the proof is not simpler.
- `react-hook-form` and `zod` for auth/form interaction validation.
- `tailwindcss`.
- Radix primitives only for controls actually used.
- shadcn components are generated source, not a blanket runtime framework.

### Frontend test/quality: adopt

- `openapi-typescript` as a development dependency.
- Redocly CLI for OpenAPI linting and static HTML documentation artifacts.
- Pinned `oasdiff` tooling for breaking-contract detection.
- `vitest`.
- `@testing-library/react`, `@testing-library/user-event`, and `@testing-library/jest-dom`.
- `playwright` for browser/map/auth/reveal flows.
- `axe-core` Playwright integration for accessibility checks.
- Next.js-supported ESLint configuration.
- `prettier` unless the selected Next.js toolchain supplies one accepted formatter.

### Workspace/tooling: adopt

- `uv` for Python dependency locking and commands.
- `pnpm` with Corepack for the web workspace.
- Docker BuildKit and Docker Compose.
- PostgreSQL/PostGIS image pinned by digest/version policy.
- Caddy image pinned by digest/version policy.
- GitHub Actions and GHCR.
- Trivy for images/filesystems.
- Gitleaks for accidental credentials.
- Dependabot for manifests/actions/images plus the documented merge controller.

### Initial repository and container bootstrap boundaries

The requested starter repository setup is valid only as the following ordered, independently reviewed work. It is not one cross-task bootstrap commit:

1. E1-T1 owns Git initialization, the canonical remote, root `.gitignore` and `.dockerignore`, a safe `.env.example`, and a concise root `README.md` linking this documentation. These safety controls must exist before any generated scaffold or Docker build context.
2. E0-T2 owns the approved synthetic architecture proof, runtime/dependency manifests and lockfiles, and measured Docker builds needed to validate the selected boundaries. It must not add a generic placeholder service that will be discarded.
3. E1-T2 turns the accepted proof into the minimal FastAPI and Next.js application scaffolds and their development/production Dockerfile targets. It introduces root Make targets only for real install/format/lint/type-check/test/contract/build commands that now exist.
4. E1-T3 adds the local Compose topology only after the application commands and health endpoints exist. Compose then wires `web`, `api`, PostGIS, optional Caddy, and an on-demand importer without inventing substitute commands, and extends the Makefile with real Compose/operator targets.

Each task uses its own branch and commit/PR boundary. The canonical M1 dependency order remains E1-T1 before E0-T2, E0-T2 before E1-T2, and E1-T2 before E1-T3.

Bootstrap artifact rules:

- The root `.gitignore` excludes source exports, archives, media, generated sensitive reports, local databases, environment files, Telegram sessions, caches, coverage, build outputs, and editor/OS noise without hiding committed lockfiles or the generated OpenAPI contract.
- The root `.dockerignore` makes the repository build context safe by excluding Git metadata, source data/media, secrets, local databases, caches, test artifacts with sensitive material, and unrelated generated output. A Dockerfile may use a narrower application context when that does not prevent reproducible workspace installs.
- Dockerfiles use named multi-stage targets, locked installs, maintained base images pinned under the dependency-update policy, non-root runtime users, explicit entry commands, and no source export, secret, documentation generator, or development-only dependency in final runtime layers.
- Build credentials, if ever required, use BuildKit secret mounts. They are never Docker build arguments, persistent environment values, copied files, or cache content.
- Local Compose uses a WEF-scoped project name, no explicit `container_name`, one internal network, only the intended edge port, and named volumes for PostGIS and generated media. The source export is an explicit read-only importer mount and is unavailable to public application services.
- Health checks guard dependency readiness; long-form `depends_on` may use `service_healthy`, while one-shot prerequisites may use `service_completed_successfully`. Restart order is not treated as application-level resilience.
- Optional or operator-only services use Compose profiles where that improves the default path. The Telegram worker remains disabled until Epic 8, and Caddy may remain optional for direct local development.
- The root `Makefile` is a thin, documented command façade, not an alternative build system. Targets are added only when their underlying commands exist; expected eventual targets cover help, install, format, lint, type-check, test, contract generation/check, image build, Compose up/down/logs, and explicit importer dry-run.
- The root `README.md` states prerequisites, safe setup, common commands, architecture/documentation links, source-data exclusions, and the approval/branch policy. It must not duplicate domain documentation or imply that proposed tasks are implemented.
- `.env.example` contains names, safe examples, and comments only. Runtime secrets and production values remain outside Git.

### Implement internally

These are project policy and should not be delegated to generic dependencies:

- Offer filter/range/facet semantics.
- Cursor format and pagination policy.
- Geocoder provider abstraction/cache/review policy.
- Contact reveal authorization/audit/rate-limit policy.
- CSRF/origin/session security policy around cookie-authenticated mutations.
- Telegram/source URL policy.
- Import reconciliation/checkpointing.
- Unit-of-work and narrow repository ports.
- API presenter mapping.

### Explicitly reject for MVP

- Django/DRF: duplicates the accepted FastAPI stack.
- A separate Node backend or Next.js business API.
- Redis and Redis-backed rate-limit/session/cache libraries.
- Celery/RQ/Arq/Dramatiq.
- Elasticsearch/OpenSearch.
- GraphQL.
- Third-party DI containers.
- FastAPI Admin because its TortoiseORM/Redis stack conflicts with accepted SQLAlchemy/no-Redis architecture.
- Unrestricted generic admin CRUD over users, sessions, contacts, or audit tables.
- Event bus/message broker.
- Generic repository/service frameworks.
- Full CQRS/event sourcing.
- Redux/Zustand.
- Microservices/Kubernetes/service mesh.
- Heavy self-hosted geocoder on the shared NUC.

Replacement paths for rejected groups:

| Rejected group | Accepted replacement |
|---|---|
| Django/DRF, separate Node backend, or Next.js business API | FastAPI backend-centric modular monolith and generated REST/OpenAPI contracts |
| Redis sessions/cache/rate limiting and background-job frameworks | PostgreSQL-backed sessions/idempotency, bounded in-process controls, and explicit operator/import commands until a measured scale trigger |
| Elasticsearch/OpenSearch and GraphQL | PostGIS/SQL projections exposed by the versioned REST API |
| Third-party DI, generic repository/service frameworks, full CQRS/event sourcing, or an event bus | Explicit composition, narrow inward-owned ports, interactors/query services, and unit-of-work boundaries |
| FastAPI Admin or unrestricted generic admin CRUD | Starlette Admin with project-owned authentication, authorization, CSRF/session controls, and narrow owner actions |
| Redux/Zustand | URL state plus TanStack Query server state and local component state |
| Microservices/Kubernetes/service mesh | One Docker Compose deployment with independently testable package boundaries |
| Heavy self-hosted geocoder | Managed free-tier provider behind the geocoder port, persistent cache, and manual review workflow |

## Dependency acceptance criteria

Every adopted dependency must:

- Have a clear single responsibility and remove more risk/code than it adds.
- Be actively maintained and compatible with the chosen runtime.
- Have an acceptable license for the repository/deployment.
- Support containerized Linux and ARM/AMD build expectations if required.
- Avoid mandatory external paid infrastructure for anonymous MVP browsing.
- Be pin-able and scannable.
- Not bypass architecture boundaries.
- Not expose source/contact/secrets through default logging.

Proposed E0-T2 acceptance requires recording the package, version, license, purpose, direct/transitive risk, and replacement path before locking.

## Proposed post-approval implementation proof

Only after this spike and the E0 implementation plan are explicitly owner-approved, proposed task E0-T2 would create this minimal non-product proof on its dedicated task branch:

1. One feature module with domain, application query/interactor, port, SQLAlchemy adapter, route, and presenter.
2. One PostGIS-backed integration test.
3. One `import-linter` contract proving forbidden inward dependencies fail.
4. FastAPI OpenAPI exported as a deterministic CI artifact.
5. The schema is committed at `contracts/openapi/v1.json`; production schema/Swagger/ReDoc routes are disabled.
6. `openapi-typescript` generates web types and `openapi-fetch` compiles a request.
7. Redocly lint/static HTML and `oasdiff` compatibility checks run without entering runtime images.
8. One Next.js component renders the returned DTO without recomputing a business rule.
9. One English `next-intl` key renders in a Server Component and Client Component.
10. Lockfiles, license/advisory scans, Docker builds, lint, type checks, and tests pass.

The proposed proof may use a synthetic location/offer and must not import the real dataset. This is candidate implementation scope and acceptance, not code authorized by this research artifact.

## Proposed E0-T2 implementation deliverables

- Final backend/frontend/runtime dependency manifests and lockfiles.
- Dependency/license/advisory report.
- Accepted package-by-feature layout.
- Architecture import contracts.
- Composition-root example.
- OpenAPI generation/client contract check.
- Decision note for any dependency changed from this proposal.
- Measured build/install/test output.
- Refined implementation tasks with dependencies and acceptance criteria.

## Proposed E0-T2 acceptance baseline

If promoted and included in a separately owner-approved implementation plan, E0-T2 would be accepted when:

- Backend/frontend responsibility boundaries are approved.
- Route, interactor, domain service, repository/query, unit-of-work, presenter, and adapter responsibilities are demonstrated.
- The frontend consumes generated types and only renders/formats backend decisions.
- Import boundaries fail CI when deliberately violated.
- Dependency versions/licenses/advisories are captured and lockfiles are reproducible.
- No source data, media, credential, or production service is touched.
- Affected architecture, decision, contract, and workflow documents are updated with any conclusion that changed during the approved proof.


## Promoted task boundaries

- [E0-T1: Review architecture and dependency proposal](tasks/E0-T1-review-architecture-and-dependency-proposal.md) — promoted after spike approval; review this research, affected contracts, and ADR-012.
- [E0-T2: Execute and lock the architecture proof](tasks/E0-T2-execute-and-lock-the-architecture-proof.md) — promoted after spike approval; bounded synthetic proof, lockfiles, architecture checks, generated contract, and measured toolchain evidence.

Promotion does not authorize implementation. E0-T1 cannot start until the implementation plan is approved and E1-T1 is done. E0-T2 cannot start until the implementation plan is approved, E0-T1 and E1-T1 are done, and its dedicated branch/state gates pass.

## Research risks and open questions

- Confirm maintained runtime/package versions, licenses, advisories, and ARM/AMD container compatibility during approved E0-T2 work rather than asserting unverified pins here.
- Decide from measured proof evidence whether FastAPI Users and `nuqs` remove more complexity than they add.
- Choose testcontainers versus a CI PostGIS service and lightweight factories versus factory-boy from reproducible CI evidence.
- Decide the exact Make targets and Compose profiles only after E1-T2 fixes the real application commands; do not create no-op or throwaway bootstrap commands.
- Validate the final `.gitignore`/`.dockerignore` against the actual source-data paths and inspect image contexts before the first commit or build.
- Record any change to architecture direction, public/persisted contracts, identity/security boundaries, or deployment assumptions through the workflow invalidation rules.

## Spike invalidation triggers

- A change to backend/frontend ownership, dependency direction, package-by-feature boundaries, transaction ownership, or presenter/interactor responsibilities.
- A material dependency substitution that changes persisted/public contracts, security behavior, ingestion semantics, or deployment topology.
- A decision that introduces microservices, a broker, Redis, a second business API, or frontend-owned domain rules.

## Spike exit checklist

- [x] The bounded architecture/dependency question is answered as a research recommendation.
- [x] Verified documentation findings, recommendations, and implementation acceptance are distinguished.
- [x] Affected architecture, contract, governance, security, and decision documents are linked through this epic.
- [x] E0-T1 and E0-T2 candidate boundaries and dependencies are identified.
- [x] Initial repository, Dockerfile, Compose, Makefile, README, branch, and task-ownership boundaries are explicit.
- [x] No production or disposable proof code is authorized or represented as already executed.
- [x] `revision: 2` represents the material content submitted.
- [x] Revision 2 received explicit owner approval and the approval metadata matches this revision.

## Owner decision

Flippylolz explicitly approved revision 2 on 2026-08-12. This approval permits task refinement/promotion and implementation planning; it does not permit E0-T2 or any other code.
