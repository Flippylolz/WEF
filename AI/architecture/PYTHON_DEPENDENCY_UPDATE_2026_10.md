# October 2026 Python dependency refresh

This is unplanned maintenance requested by the owner on 2026-10-19 as part of
repairing the open Dependabot PRs and running current stable dependencies.
The lockfile was refreshed against PyPI for every direct runtime and development
package and its dependencies. Notable versions are FastAPI 0.146.0, SQLAlchemy
2.1.5, Pillow 13.0.0, cryptography 50.0.2, Pydantic 2.14.1, uvicorn 0.54.0,
Telethon 1.45.0, Ruff 0.17.1, and mypy 2.4.0. No direct package is added.

SQLAlchemy 2.1's typing requires explicit UUID result casts for PostgreSQL insert
results and explicit tuple construction for media replay keys. These changes
preserve runtime behavior and are covered by the existing import/media suites.

The framework regenerates Decimal schemas without its former restrictive
regular expression and marks the frozen LocationAccuracy projection as closed.
The OpenAPI compatibility check reports no breaking changes. Generated
TypeScript remains synchronized; application validation and routes are unchanged.

Dependabot now uses the supported `uv` ecosystem for `uv.lock`, replacing `pip`.
The existing configuration regression test and repository policy match that
choice. Weekly grouping and the merge controller's gates are preserved.
See [uv's Dependabot integration](https://docs.astral.sh/uv/guides/integration/dependabot/).

No database, environment, or deployment migration is needed. Rollback is a
squash-commit revert restoring the lockfile, typing, and generated schemas.
