# October 2026 form resolver major update

The owner requested current stable dependency versions. This unplanned update
moves the existing `@hookform/resolvers` package from 5.9.2 to 6.0.0 separately
from routine patch/minor updates. It depends on frontend refresh PR #407, which
provides the current React Hook Form and Zod releases; it must merge afterward.

The upstream stable GitHub release and npm metadata were verified on 2026-10-19.
The release was published that morning, so pnpm records an exact-version age
exception for `@hookform/resolvers@6.0.0` in `pnpm-workspace.yaml`. Other dependency
trust and installation policies remain unchanged. No direct package is added.

The integration retains backend-owned authentication behavior and the existing
Zod form schemas. Validation covers type compatibility and the existing login,
registration, password-change, validation, server-error, accessibility, and full
application test cases, plus a production build and dependency audit. Required
current-head CI remains the merge gate.

No API, database, configuration, or deployment migration is needed. Rollback is
reverting this PR's squash commit to restore the preceding resolver and lock.

Local verification passed with 1,468 backend and 191 frontend tests, both coverage
floors intact, and clean production dependency audit. The Node 22.23.3 production
build is 570,497 gzip bytes across 16 JavaScript chunks, below the unchanged
599,617-byte limit. Format, lint, type, and generated-contract checks pass.
