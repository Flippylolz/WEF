# Application boundary coverage

The owner's repository-wide 100% request also covers executable behavior outside
application packages. This pass measures handwritten migrations, the backend-owned
owner map, frontend build configuration and both frontend command scripts. It
preserves every existing 100% gate and adds no coverage exclusions or dependencies.

## Verified scope

The locked backend suite passes 2,266 tests. Its complete package and migration
inventory covers all 18,839 statements and 3,930 branch paths. All 262 executable
backend Python files independently require 100%; both `wef_backend` and `migrations` are
included in local pytest, Compose and shared CI commands.

The locked frontend suite passes 355 tests. Every measured file requires 100% of
lines, statements, functions and branches. The report includes 1,508 lines, 1,662
statements, 427 functions and 1,418 branch paths. The added source entries are:

- `apps/backend/src/wef_backend/features/admin/interface/statics/place_picker.js`.
- `apps/web/next.config.ts`.
- `apps/web/scripts/check-frontend-boundaries.mjs`.
- `apps/web/scripts/prepare-standalone-e2e.mjs`.

Vitest explicitly enables external-file coverage for the backend-owned browser
asset. The frontend test service mounts that single script read-only; the frontend
production build context retains its existing backend-source boundary. The
standalone preparation helper is admitted to the narrow frontend build context
so the test imports also resolve during image builds.

A source file with executable lines and no conditional paths has zero branch
counters. The critical-file checker accepts that valid empty branch metric while
still requiring every executable line. Missing files, empty line counters, invalid
counters and uncovered lines remain failures.

## Behavioral evidence

Six real Alembic rehearsals check an empty schema's complete upgrade/downgrade/
upgrade round trip, comparing columns and indexes. Populated archive recovery,
channel progress and raw-event retry history each refuse downgrade and preserve
both the evidence and current revision. Offline SQL generation runs with and
without an explicit logging configuration. Destructive rehearsals reject every
database name except reserved `wef_test`; CI now uses that same disposable name.
Fixture cleanup retains PostGIS and Alembic metadata.

Twenty-eight browser tests check pin placement, pointer ownership, drag versus
click, zoom bounds, input synchronization, wrapped tiles, offscreen pins, resize,
missing controls and tile-error notices. They use synthetic coordinates and local
DOM events without provider requests.

The build tests check publication of both pinned MapLibre worker assets, refusal
on a failed copy, standalone tracing boundaries, real TypeScript import graphs,
cycle rejection and actual gzip budget accounting. Standalone preparation refuses
a missing server before copying assets. Node mocks replace filesystem side effects;
source parsing and compression use their real implementations.

Two equivalent simplifications remove impossible paths: the parser-replay migration
executes its fixed list of four nonblank SQL literals directly, and dependency
traversal reads graph entries that were guaranteed by source admission and graph
construction. SQL, dependency resolution and cycle refusal retain their behavior.
No coverage pragma is added.

## Validation and remaining work

The locked `make format-check lint typecheck test contract-check quality-gates
compose-config` run passes, including 2,266 backend tests, 355 frontend tests and
198 operational policy/proof tests. The release-workflow proof also passes. Policy
tests reject narrowed migration, browser and build inventories or disabled
external-asset measurement.

Operational Python and shell remain part of the active repository-wide goal.
Documentation, generated declarations, static assets, declarative configuration
and test/proof drivers have no application behavior to instrument. Operational
commands and deployment/transfer guards remain in scope.
