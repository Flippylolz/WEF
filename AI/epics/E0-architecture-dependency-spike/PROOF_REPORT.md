# E0-T2 Architecture Proof Report

- Executed: 2026-08-12
- Scope: synthetic, non-production architecture/dependency proof
- Task: [E0-T2](tasks/E0-T2-execute-and-lock-the-architecture-proof.md)
- Runtime pins: Python 3.13.2, Node.js 22.22.2, uv 0.12.3, pnpm 11.21.0
- Lockfiles: `apps/backend/uv.lock`, `pnpm-lock.yaml`

## Outcome

The proof validates the approved backend-centric modular monolith without reading real exports, media, contacts, credentials, Telegram sessions, or production services.

The implemented request flow is:

```text
GET /api/v1/estates
  -> FastAPI route
  -> ListEstates query service
  -> application-owned EstateQueryPort
  -> SQLAlchemy/PostGIS adapter
  -> application DTO with backend-owned availability label key
  -> pure Pydantic presenter
  -> generated TypeScript contract
  -> openapi-fetch request
  -> Next.js Server Component
  -> next-intl Client Component
```

The domain and application packages do not import FastAPI, Pydantic, SQLAlchemy, GeoAlchemy, or infrastructure. Import Linter enforces inward layer direction and rejects a temporary deliberate framework import into the domain.

## Evaluated dependency conclusions

| Candidate | Conclusion | Evidence and replacement path |
|---|---|---|
| FastAPI Users | Omit from the architecture foundation | Authentication is outside this proof, and adapting email-oriented defaults adds an unproven boundary. The auth epic will use focused project-owned username/session code unless its approved spike demonstrates lower risk from the dependency. |
| `nuqs` | Omit from the proof baseline | The proof has no product filters and needs no URL-state abstraction. E5 may add it only if measured filter code is simpler than direct `URLSearchParams`. |
| Testcontainers | Use a pinned CI PostGIS service instead | The integration test accepts only an explicit disposable `TEST_DATABASE_URL`; CI starts pinned `postgis/postgis:17-3.5`. This avoids Docker-socket coupling in test code. |
| `factory-boy` | Use lightweight project fakes/factories | Typed dataclasses and small fixtures cover the proof without framework-specific factories. Add a library only when fixture relationships demonstrate enough repeated complexity. |

These conclusions do not change the accepted architecture or public/security boundaries.

## Direct runtime dependencies

### Backend

| Package | Locked version | License | Responsibility | Replacement path |
|---|---:|---|---|---|
| FastAPI | 0.141.1 | MIT | HTTP routing and OpenAPI | Starlette plus project schema wiring, only if FastAPI becomes incompatible |
| Uvicorn | 0.52.1 | BSD-3-Clause | ASGI process | Another maintained ASGI server |
| Pydantic Settings | 2.15.0 | MIT | Environment-backed settings | Focused standard-library loader |
| SQLAlchemy | 2.0.52 | MIT | Async persistence adapter | SQLAlchemy Core or focused asyncpg adapter |
| asyncpg | 0.31.0 | Apache-2.0 | PostgreSQL async driver | Maintained SQLAlchemy-compatible PostgreSQL driver |
| Alembic | 1.19.1 | MIT | Future forward migrations | Versioned project SQL migrations |
| GeoAlchemy2 | 0.20.0 | MIT | PostGIS types/functions | SQLAlchemy expressions with explicit PostGIS SQL |
| structlog | 26.1.0 | MIT OR Apache-2.0 | Structured runtime events | Standard logging with project JSON formatter |

### Frontend

| Package | Locked version | License | Responsibility | Replacement path |
|---|---:|---|---|---|
| Next.js | 16.3.0 | MIT | App Router/server rendering/build | React server/client application with explicit routing |
| React | 19.2.8 | MIT | UI rendering | No practical in-scope replacement without a new frontend ADR |
| React DOM | 19.2.8 | MIT | Browser/server DOM rendering | Coupled to the selected React stack |
| next-intl | 4.13.6 | MIT | Fixed-English server/client message lookup | Project message lookup using standard `Intl` APIs |
| openapi-fetch | 0.17.0 | MIT | Typed generated-contract requests | Small project fetch wrapper over generated types |

The production frontend transitive inventory contains MIT, Apache-2.0, BSD, ISC, 0BSD, CC-BY-4.0, and LGPL-3.0-or-later metadata. The LGPL entry is the dynamically packaged libvips dependency of Next.js image tooling; preserve dependency notices in a later release artifact. Direct backend runtime dependency metadata is fully identified; transitive Python metadata includes some legacy classifier-only/unknown fields that require generated notice normalization before a public binary distribution.

## Contract result

- FastAPI generates deterministic sorted JSON at `contracts/openapi/v1.json`.
- Runtime `openapi_url`, Swagger UI, and ReDoc routes are disabled.
- `openapi-typescript` generates and checks `apps/web/src/generated/api.ts`.
- `openapi-fetch` compiles and requests `GET /api/v1/estates`.
- Redocly recommended lint passes and produces a standalone HTML artifact outside runtime images.
- oasdiff 1.28.0 reports no breaking change against the available baseline/current schema.

## Verification evidence

| Check | Result |
|---|---|
| Backend format/lint | Ruff: 29 files formatted; all checks passed |
| Backend type check | mypy strict: 29 source/test/script files; no issues |
| Architecture | 3 Import Linter contracts kept; deliberate domain→FastAPI import rejected and cleaned |
| Backend tests | 15 passed against a disposable PostGIS 17/3.5 container |
| Coverage | 96.10% branch-aware coverage; threshold 90% |
| Python advisory scan | pip-audit: no known vulnerabilities |
| OpenAPI | deterministic export; Redocly validation passed |
| Frontend contract | generated type check passed |
| Frontend quality | TypeScript, ESLint, 3 Vitest tests, and Next.js production build passed |
| Node advisory scan | `pnpm audit --prod --audit-level high`: no known vulnerabilities |
| Compatibility | oasdiff 1.28.0: no changes detected for proof baseline |
| Backend image | 231,117,063 bytes on local arm64; non-root `wef`; no uv/pytest/mypy/Ruff in runtime |
| Web image | 197,736,763 bytes on local arm64; non-root `node`; no source/contracts/docs generators in runtime |

The targeted `.github/workflows/e0-architecture-proof.yml` repeats the checks with a real pinned PostGIS service and uploads static API HTML. Docker bases and proof service/tool images are version-and-digest pinned.

## Boundaries and follow-up

- The proof schema/table is disposable and has no production migration.
- The frontend is a contract/rendering proof, not the interactive MapLibre product.
- There is no Compose topology or production configuration in E0-T2.
- E1-T2 may refine the proof into application scaffolds without changing the demonstrated dependency direction.
- E1-T3 owns local Compose.
- E2–E5 own historical parsing, production data model/media/geocoding, read contracts, and the interactive map.
- E0-T2 remains unable to complete/merge until E1-T1 and E0-T1 are integrated and its dependency gate becomes `satisfied`.
