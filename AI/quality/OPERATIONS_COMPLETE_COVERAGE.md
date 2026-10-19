# Complete measured operational Python coverage

The operational Python suite reaches exactly 100% of all 4,694 statements and
1,456 branch paths across `scripts`. All 54 executable files have independent 100%
floors. The global `coverage.operations.toml` report floor is now 100%; Repository
safety CI rejects a lower/missing global floor, a removed per-file floor, narrowed
source/branch/subprocess measurement or an expanded exclusion allowlist.

Twenty-six new cases cover the remaining diagnostic, inventory, rollback,
configuration-rendering, smoke, asset, repository-link and badge paths. Together
with the previous suites, all 355 operational tests pass in the native diagnostic.
The existing 46 type-checking/protocol-only exclusions remain unchanged. Root
unit-test files, proof drivers and the browser runner remain test infrastructure;
no runtime Python file was omitted to reach the target.

## Redirect safety correction

The new smoke regressions reproduced two false-positive redirect checks:
`https://wef.test.evil.test/` and `https://wef.test@evil.test/` passed the old text
prefix check. Parse the URL and require HTTPS, the expected case-insensitive
hostname, no userinfo and an absent or valid positive port. Malformed URL/port
syntax remains a bounded smoke failure. Valid explicit ports and paths/queries
remain supported, with the existing bounded retry behavior. No host, listener,
certificate or live routing configuration was changed by these tests.

This corrects the existing [E7-T9 invalid-redirect refusal](../epics/E7-production-delivery/tasks/E7-T9-implement-reversible-shared-edge-cutover.md)
under the owner's unplanned repository-wide coverage request. The parser uses the
standard library; production dependencies and application contracts are unchanged.

## Assertions

- Passive Telegram observations normalize identifier types, preserve unknown
  metadata, reject unavailable collection/invalid JSON and project source-free
  status. Tests never connect to Telegram or a worker.
- Operator diagnostics redact nested mappings/lists, handle empty filesystems and
  missing state, and restrict import lookup to aggregate fields through fixed argv.
  All Docker/database commands are replaced with synthetic results.
- Server inventories accept expected WEF changes and reject unrelated identity,
  project, container, listener, HTTP, path/UID/mode and media-symlink drift.
- Rollback verification reads complete synthetic manifests, state, private config,
  current links and persistence roots; missing services/listeners, unhealthy
  containers and corrupt identities refuse successful restoration.
- Rendering validates ACME fixture/production boundaries, optional upstreams,
  template newlines, release paths and safe CLI creation. It never invokes Certbot
  or applies a configuration.
- Route smokes assert fixture bodies, independent WEF/Forecast checks, redirect
  authority, retry bounds and pre-redirect HTTP behavior through recording clients.
- The Markdown checker enumerates synthetic Git results and checks local, encoded,
  anchored, absolute, deleted and missing targets. It never changes Git state.
- Deployment-gate tests preserve existing authorization and truthful reasons/merge
  timestamps for fixture API responses; they cannot trigger deployment.
- Badge parsing rejects malformed objects/counters and preserves exact coverage
  floors and colors. MapLibre CLI tests read invented assets without executing JS.

Actual CLI subprocesses only use temporary fixtures or print helper guidance. The
Markdown entrypoint uses `runpy` with fake Git enumeration, so the locked Python
image needs no Git installation for that unit case. No real host/account/provider,
artifact download or deployment is accessed by these new tests.

## Remaining repository scope

Backend and frontend already enforce 100% independently across their documented
inventories. Measured operational Python now does too. Runtime shell and substantive
embedded Python still require inventory, instrumentation and cases before completing
the owner's repository-wide goal. Documentation, declarative configuration,
generated contracts, styles, images and test/proof drivers remain non-runtime
coverage scope; their applicable validation checks still run.

## Validation

The full locked `make format-check lint typecheck test contract-check quality-gates
compose-config` passes: 2,266 backend and 355 frontend tests retain 100%, and all
355 operational tests cover every measured statement/branch at 100%. All 54
executable operational files are present in the independent policy and pass their
floors. Global-floor removal/weakening and each newly completed file's removal are
rejected by deliberate policy faults. Strict Ruff/mypy, Markdown links and Git
whitespace checks also pass. Reports remain ignored under `tmp/coverage/`.
