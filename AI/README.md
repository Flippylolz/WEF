# Warsaw Estate Platform

`AI/` is the planning and governance source of truth for a small, Dockerized platform that turns a Telegram real-estate channel export into a searchable map of Warsaw developments and their related offers. This page is the root navigation hub; each domain owns its detailed documentation through its `README.md`.

The documentation migration is complete. Canonical content lives in the domain directories below, and `AI/README.md` is the only Markdown document allowed directly under `AI/`.

## Confirmed product decisions

- A map pin represents a normalized location or development and opens the related offers.
- Offers show their Telegram publication date prominently.
- Imported posts are not described as currently available unless a future source provides a reliable availability signal.
- Browsing is public/read-only. Pseudonymous username/password accounts are required only for restricted actions such as audited contact reveal, and administration is restricted to the fixed owner role.
- The initial map covers Warsaw. Out-of-area records remain importable but are excluded from the default map.
- English is the initial UI language and all user-visible strings use i18n keys for future translations.

## Confirmed technical decisions

- Backend and ingestion: Python with FastAPI.
- Frontend: TypeScript with Next.js.
- Architecture: a backend-centric, package-by-feature modular monolith with interactors, presenters, service objects, narrow ports/adapters, and enforced SOLID/DRY dependency boundaries; the frontend primarily renders and localizes generated API contracts.
- API contract: deterministic FastAPI OpenAPI committed in the repository and emitted as CI JSON, generated types, and static HTML artifacts; Swagger, OpenAPI, and ReDoc routes are disabled in production.
- Map renderer: MapLibre GL JS with OpenFreeMap as the initial basemap.
- Database: PostgreSQL with PostGIS.
- Runtime: Docker Compose on one server, with Caddy at the edge.
- Delivery: GitHub Actions, GitHub Container Registry, and SSH deployment.
- Production configuration: GitHub Actions variables and secrets are the deploy configuration source of truth. Complete validated configuration is transferred atomically on every deploy; no production `.env` is committed.
- Reliability scope: application data persists on the NUC, but backups and restore drills are deferred. Persistence is not backup, and the accepted single-host data-loss risk must not be presented as a recovery guarantee.
- Repository governance: feature branches, pull requests, and CI checks are mandatory procedurally. GitHub-enforced branch protection is unavailable/out of scope under the accepted account-plan constraint.
- Delivery sequencing: approved dependent tasks may continue in ordered stacked pull requests without waiting for upstream review/merge; child tasks cannot be completed or merged before their dependencies.
- Authentication and administration: pseudonymous username/password accounts, database-backed secure sessions, and an owner-only user/audit console; no owner credential is committed or hardcoded.
- Live Telegram integration: a later Telethon worker uses the same canonical ingestion pipeline as the historical export.

## Domain navigation

- [Product](product/README.md) — scope, experience requirements, quality, and acceptance.
- [Data](data/README.md) — source baseline, quality, retention, and readiness.
- [Contracts](contracts/README.md) — canonical data model, HTTP API, and OpenAPI generation.
- [Architecture](architecture/README.md) — system boundaries, runtime shape, and dependency baseline.
- [Ingestion](ingestion/README.md) — historical/live pipelines and geocoding.
- [Security](security/README.md) — username/password accounts, owner administration, contact masking, reveal, and audit.
- [Operations](operations/README.md) — deployment, server baseline, persistence, and operational constraints.
- [Governance](governance/README.md) — repository and change rules.
- [Decisions](decisions/README.md) — ADR/deferred-decision registry and supersession graph.
- [Milestones](milestones/README.md) — outcome checkpoints M1–M4.
- [Epics](epics/README.md) — delivery workspaces, proposed tasks, dependencies, and traceability.
- [Workflow](workflow/README.md) — approval-gated lifecycle, artifact schemas, templates, and definition of done.

## Required delivery lifecycle

Work proceeds in this order:

1. Select one epic.
2. Complete its documentation/research-only spike.
3. Record explicit owner approval of the current spike revision.
4. Refine proposed tasks and promote approved candidates inside that epic.
5. Complete the epic implementation plan.
6. Record explicit owner approval of the current implementation-plan revision.
7. Implement code task by task, using one branch per task and only after every dependency is done.

No production code or disposable proof code is allowed before implementation-plan approval. Files under `proposed-tasks/` are non-actionable.

## Source-of-truth precedence

When documents disagree, use this precedence:

1. Accepted records in [decisions](decisions/README.md).
2. Product behavior and acceptance in [product](product/README.md).
3. Public/persisted contracts in [contracts](contracts/README.md), then system boundaries in [architecture](architecture/README.md).
4. Domain behavior and constraints in [security](security/README.md), [ingestion](ingestion/README.md), and [operations](operations/README.md).
5. Repository/change rules in [governance](governance/README.md).
6. Approved sequencing and execution records in [epics](epics/README.md) and [workflow](workflow/README.md).

The [data](data/README.md) domain records source evidence and readiness. If it conflicts with a higher-precedence decision, product rule, contract, or ingestion rule, resolve the conflict in those authoritative domains rather than silently changing the evidence.

Changes that alter product behavior, public API contracts, persisted data, security, or deployment topology require a new decision record and updates to every affected document. An approved spike or implementation plan is valid only for its recorded revision; material changes follow the invalidation rules in the workflow.

## Terminology

- **Source message**: an immutable representation of a Telegram post or service event.
- **Offer**: one dated real-estate proposition parsed from a source message. An offer may describe a development or an individual unit.
- **Location**: a normalized, geocoded place used for a map pin.
- **Development**: a named or inferred project associated with a location. A location can exist without a known development name.
- **Pin**: the map representation of a location/development, with one or more related offers.
- **Imported**: successfully stored from a source. It does not mean currently available.
- **Published at**: the original Telegram post timestamp displayed to users.
- **Proposed task**: a candidate definition under an epic's `proposed-tasks/`; it is not approved or actionable.
- **Task**: a promoted definition under an epic's `tasks/`. It becomes actionable only when all workflow gates allow `ready` or `in_progress`.
- **Owner approval**: an explicit, attributable approval of one recorded artifact revision; silence, review activity, or approval of another revision does not count.

## Documentation maintenance

- Keep requirements testable and preserve stable ADR, deferred-decision, product requirement, milestone, epic, and task IDs.
- Keep each fact in its authoritative domain and link to it elsewhere; do not maintain duplicate sources of truth.
- Record uncertainty explicitly; do not present heuristically parsed fields as verified facts.
- Do not put credentials, Telegram sessions, phone numbers, or production values in this directory.
- Keep the raw export and all generated media outside Git and Docker build contexts.
- Resolve deferred decisions before promoting or starting a task that depends on them.
- Update affected decisions, contracts, acceptance criteria, traceability, and operational guidance in the same change.
- Keep domain navigation in each domain's `README.md`; do not create `index.md` files.
