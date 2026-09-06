# E26 additive-schema rollback prerequisite

The approved E26 rollout requires retaining a compatible application reader after
T2 adds migration `20260906_0026`. The previous readiness probe accepted only an
exact Alembic revision, which would make ordinary application rollback fail even
though T2 only adds independent tables and preserves existing columns.

This independently reviewable defect fix explicitly lets the `0025` reader accept
`0026`. It does not permit arbitrary future or unknown revisions, apply migrations,
start revalidation, or change the approved schema/budget/selection scope. When T2
changes its expected revision to `0026`, the same allowlist contains only `0026`;
the new worker cannot report ready on an unmigrated `0025` database.

Deploy this prerequisite before T2. T2 remains one implementation branch/PR; this
small prerequisite implements the existing plan's rollback guarantee. A real
PostGIS readiness test checks the explicit future revision and rejects unknown
or unapproved values. That revision-tag test alone is not a schema-compatibility
proof; verify the built prior reader against the actual T2 schema before release.

## Verification

`COMPOSE_PROJECT_NAME=wef-e26-compat make verify` passed: 1,244 backend tests,
185 frontend tests, all existing coverage floors, 186 script tests, strict
format/lint/types, contracts, negative quality gates, production/runtime/rollback
proofs, builds, architecture checks and documentation links.

The built runtime image `wef-backend:e26-compatible-reader` (expected revision
`20260906_0025`) was then run read-only against the separate real T2 test database.
That database was at `20260906_0026` and contained all three new validation tables.
The prior reader passed readiness and the actual PostGIS-backed grouped map query.
No production schema or data was changed for this proof.


The compatible reader deployed successfully through PR #365 / release
`34029703306` before T2 migration/application. The subsequent worker and provider
normalization releases succeeded. See [production rollout](PRODUCTION_ROLLOUT.md).
