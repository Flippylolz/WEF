# E14-T1 verification mapping

The owner approved E14-T1–T5 only on 2026-09-06; OWNER_DECISION.md records the scope.
T1 starts from main `2ab0c57` and does not alter product behavior or schema.

`make verify` installs locked dependencies and runs format, zero-warning lint,
strict types, backend/PostGIS and frontend coverage suites, generated contract
checks, negative governance probes, OpenAPI compatibility and its breaking probe,
Compose/production configuration proofs, production image builds, the architecture
violation probe and Markdown links. Docker must be running and `origin/main` must
exist; a missing compatibility baseline fails instead of comparing a file to itself.
Install the recorded Python/Node versions, uv 0.10.11, pnpm 11.21.0, Git, Docker
with Compose and ShellCheck (validated with 0.11.0). The command checks executable
prerequisites up front; it installs project dependencies, not host system tools.
Production configuration proofs clear the disposable test Compose project name so
the expected production model is checked without starting production services.
Do not run multiple full suites against the same Compose project concurrently.

PR and release use `.github/workflows/verify.yml`; their runtime-image build,
image-content inspection, production topology runtime and browser jobs remain
explicit CI-only delegates. `make verify` does not claim those browser/runtime
results. E14-T5 will replace the current map-disabled critical-path journey with
the separately approved real-stack matrix. Deployment secrets and activation are
always CI/operator-only, never part of the local quality gate.

Unexpected pytest warnings are errors, with no warning exceptions. The HTTPX
per-request cookie warning was removed by using the client cookie jar. Integration
test teardown closes retained ORM sessions before engine disposal, including test
apps whose lifespan was not entered. This changes test resource ownership only;
production pool/session behavior is unchanged.

Frontend lint uses `--max-warnings 0`; unit tests reject unexpected console warnings
and errors, with explicit diagnostic probes. jsdom canvas returns null because no
canvas backend exists; it supplies no WebGL acceptance evidence. Tests intentionally
exercising console diagnostics must explicitly replace the spy in that test.

Negative configuration fixtures remove/rename required checks, mismatch Dependabot,
bypass shared verification, lower/omit coverage floors, disable warnings, remove
contract/architecture checks, remove the aggregate command, and introduce warning suppression. Each must fail the checker. The checker detects configuration
drift; it is not a security proof against arbitrary hostile workflow programs.
