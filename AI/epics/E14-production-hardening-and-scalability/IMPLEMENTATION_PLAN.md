---
schema: ai-workflow/implementation-plan@1
epic: E14
title: "Production hardening and scalability delivery"
status: awaiting_approval
revision: 1
owner: owner
spike_revision: 1
task_sequence:
  - id: E14-T1
    revision: 1
  - id: E14-T2
    revision: 1
  - id: E14-T3
    revision: 1
  - id: E14-T4
    revision: 1
  - id: E14-T5
    revision: 1
  - id: E14-T8
    revision: 1
  - id: E14-T6
    revision: 1
  - id: E14-T7
    revision: 1
approval:
  required_role: owner
  status: pending
  decided_by: null
  decided_at: null
  approved_revision: null
  evidence: null
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Production hardening and scalability delivery

## Approved spike baseline

[E14 spike revision 1](SPIKE.md) is owner-approved under AD-041 and remains current.
The binding direction is incremental, evidence-led hardening of the existing modular
monolith: protect behavior before refactoring, define reliability/capacity budgets
before scaling, keep business behavior backend-authoritative, and do not claim
backup/recovery while ADR-015 and E7-T5 remain deferred.

## Scope and outcome

This plan authorizes eight independently reviewable tasks. It makes the quality gate
fail closed, strengthens risk-weighted tests, decomposes the largest frontend/backend
orchestration seams without behavior changes, adds real cross-browser full-stack
journeys, produces digest-bound supply-chain evidence, adds privacy-bounded SLO
telemetry/alerts, and establishes repeatable capacity and performance budgets.

E14-T9 is deliberately excluded. It remains proposed/non-actionable until a separate
owner decision supersedes or amends ADR-015, promotes/completes E7-T5, and approves
backup destination, encryption/key custody, retention, RPO/RTO, and recurring cost.
This plan cannot complete E14 or M5 without that later recovery revision.

## Ordered task sequence

1. [E14-T1](tasks/E14-T1-make-quality-and-governance-gates-truthful.md) establishes
   one canonical `make verify` entry point and executable consistency/negative probes.
   It has no task dependency and becomes the gate used by every descendant.
2. [E14-T2](tasks/E14-T2-strengthen-critical-path-test-confidence.md) adds the risk
   matrix, focused coverage floors, deterministic repeats, and deliberate-fault probes.
   It depends on T1 so the new confidence checks cannot silently drift.
3. [E14-T3](tasks/E14-T3-refactor-frontend-orchestration-hotspots.md) characterizes
   and extracts frontend seams. E13-T3 is already done; T2 must complete first.
4. [E14-T4](tasks/E14-T4-refactor-backend-ingestion-and-operator-seams.md) characterizes
   transaction/CLI behavior and extracts ingestion/operator responsibilities after T2.
5. [E14-T5](tasks/E14-T5-add-full-stack-cross-browser-and-accessibility-journeys.md)
   adds the real browser-to-web-to-API-to-PostGIS matrix after T3 and T4 stabilize seams.
6. [E14-T8](tasks/E14-T8-harden-supply-chain-and-release-integrity.md) adds SBOM,
   image scanning, dependency-diff, release-manifest, and migration/startup proofs.
   Its only dependency is T1, but it lands here so application-refactor CI is stable.
7. [E14-T6](tasks/E14-T6-define-slos-and-ship-privacy-safe-observability.md) defines
   SLOs and delivers bounded metrics/Web Vitals/alerts. It remains blocked until both
   E8-T5 and T1 are `done`; merged E15 work does not silently satisfy E8-T5 acceptance.
8. [E14-T7](tasks/E14-T7-prove-capacity-and-enforce-performance-budgets.md) uses the
   stable seams and T6 signal definitions for deterministic budgets and manual/scheduled
   capacity evidence. It depends on T3, T4, and T6.

Each task uses one branch and one pull request. Tasks may be stacked only when the
workflow's exact ancestor-PR evidence is available; completion and merging remain
dependency-order and green-CI gated.

## Modules, contracts, and migrations

- **T1:** `Makefile`, `.github/workflows/ci.yml`, release/Dependabot workflows,
  `.github/dependabot-required-checks.json`, `scripts/`, and governance/workflow docs.
  No public/persisted contract or migration.
- **T2:** backend/frontend tests, coverage configuration, synthetic builders, and
  a checked-in risk matrix. No production behavior or migration.
- **T3:** explorer/account/detail/media components and tests under `apps/web/src`.
  Generated API DTOs and URL semantics remain unchanged; no migration.
- **T4:** ingestion extraction/persistence/application modules, operator commands,
  proof/controller scripts, architecture contracts, and tests. No schema or parser
  semantic change is planned; any discovered need for one invalidates this plan.
- **T5:** Playwright config/specs, synthetic E2E seed/topology, CI artifacts, and test
  documentation. Public APIs remain compatible; disposable migrations use current head.
- **T8:** CI/release workflows, pinned actions, image build metadata, SBOM/scanner
  policies, release manifests, and compatibility scripts. Runtime image contents and
  deployment's digest-addressed contract remain authoritative.
- **T6:** backend HTTP/worker instrumentation, frontend Web Vitals sender, internal
  monitoring topology/configuration, alert rules, SLOs, dashboards/runbooks, and
  operational tests. Telemetry schemas are internal and must exclude personal/source data.
- **T7:** versioned synthetic workloads, query/plan and bundle budgets, manual/scheduled
  capacity workflow, reports, and operations/architecture thresholds. No live load target.

No data migration is planned for T1-T5/T8/T7. T6 may add only bounded internal
telemetry persistence/configuration selected below; a product-data schema change or
retention of unbounded identifiers invalidates this plan.

## Tooling and dependency selections

Approval of this plan explicitly approves only these bounded additions:

- Reuse the existing `@playwright/test` and `@axe-core/playwright` packages for T5;
  install the official Chromium, Firefox, and WebKit browser/runtime bundles in CI.
- Use checked-in deliberate-fault fixtures/scripts for T2 rather than adding a mutation
  framework or runtime dependency.
- Use pinned Anchore Syft/SBOM and Grype scan GitHub Actions (or their pinned official
  CLI containers when action eligibility is unavailable) for T8. No scanner runs inside
  production containers and no signing key/custody model is introduced.
- Add Python `prometheus-client` as the single T6 production library and pinned,
  resource-limited Prometheus plus Alertmanager containers on the internal monitoring
  network. Retain seven days locally; expose no monitoring port publicly; use bounded
  labels only. Alert delivery is configured through an owner-supplied secret webhook;
  missing delivery configuration fails operational acceptance without breaking WEF.
- Add `@lhci/cli` as a T7 development/CI-only dependency for reproducible lab budgets;
  use repository-owned Python/SQL workload scripts and existing libraries for load/query
  evidence rather than adding a production load service.

No Kubernetes, Redis, broker/queue, replica, CDN, SaaS telemetry, global frontend
store, new map vendor, or paid GitHub feature is authorized. Exact package/action/image
versions are locked and reviewed in their task PRs.

## Per-task test and evidence plan

### E14-T1

- Positive: format, zero-warning lint, strict types, architecture contracts and their
  violation probe, backend/frontend suites, OpenAPI drift/compatibility, production
  build, Compose proofs, and Markdown links through canonical/local job mappings.
- Negative: fixtures remove/rename a required check, lower/omit coverage floors, skip
  contract generation/compatibility, or bypass architecture checks; every case fails.
- Evidence: `make verify` and focused checks, workflow-consistency test output, PR CI.

### E14-T2

- Unit/integration: high-risk auth/contact/catalog/persistence/ingestion/operator failure
  paths, concurrency/cancellation/replay/idempotency, pagination/filter boundaries.
- Coverage: retain global 90% floors and enforce reviewed per-module/package floors from
  the risk matrix; every below-floor critical module needs an explicit tested rationale.
- Determinism: documented fixed-seed/repeat runs; checked-in deliberate faults for auth,
  contacts, catalog, ingestion, and release gates must be detected.

### E14-T3

- Characterize URL/query derivation, map/list selection, focus, auth/contact/favorite,
  loading/empty/error/media behavior before extraction.
- Component/hook/axe/keyboard tests protect each new typed seam; dependency-cycle and
  backend-rule-duplication checks remain clean.
- Compare production route bundles to the parent commit and reject an unexplained growth.

### E14-T4

- Characterize accepted/rejected extraction, revisions/provenance, transaction/lock
  ownership, live convergence, replay/duplicate/cancel/rollback, redaction, CLI output
  and exit codes before moving responsibilities.
- Run Ruff, strict mypy, every architecture contract plus violation probe, unit and
  PostGIS integration suites, migrations, coverage, and focused operator proofs.

### E14-T5

- Build/migrate/seed a disposable PostGIS/API/web topology with synthetic data and no
  route mocks for critical journeys.
- Run Chromium/Firefox/WebKit desktop plus mobile Chrome/Safari-emulation subsets;
  include WebGL Chromium map smoke and a separately asserted no-WebGL fallback.
- Cover filters/share URL, map/list/detail/media, registration/login/password/contact,
  favorites/logout, error recovery, keyboard/focus, axe, release identity, and artifact
  leakage scans. Upload bounded trace/screenshots/video only on failure.

### E14-T8

- Negative probes reject dependency/license policy violations, vulnerable image fixture,
  missing/mismatched SBOM/digest, unpinned input, or secret/source-bearing layer.
- Generate digest-bound SBOM and scan evidence for backend/web final images and attach
  it to the release manifest; enforce time-bounded exact exceptions only.
- Start the new images against a database migrated from the previous supported release
  and pass readiness, contract, smoke, content, permission, and provenance checks.

### E14-T6

- Unit/integration tests prove bounded label schemas, sampling/retention, redaction of
  contacts/source/query/IP/session/credentials, exporter failure isolation, Web Vitals
  delivery, and API/worker/database/edge signals.
- Prometheus/Alertmanager config tests and rehearsals fire then recover every required
  symptom alert; dashboards/runbooks identify release, latency/error, DB saturation,
  worker freshness/gaps, disk/cert, deploy, telemetry, and backup status truthfully.
- Production acceptance waits for E8-T5 completion and a configured owner alert sink.

### E14-T7

- Versioned synthetic profiles cover browse, auth/contact/favorites, ingestion burst,
  media, and mixed traffic without provider calls or personal data.
- Deterministic CI budgets cover map p95, query counts/plans, bundle/route payloads, and
  Lighthouse thresholds. Noisy concurrency/capacity runs are manual/scheduled only.
- At least three controlled runs record p50/p95/p99, errors, throughput, pool waits,
  saturation, catch-up/backlog, environment/release/dataset identity, and variance.

## Security and data safety

- All fixtures and workload profiles are synthetic. Raw Telegram messages, source media,
  contacts, sessions, credentials, production telemetry payloads, and exports stay out
  of Git, CI artifacts, SBOMs, reports, screenshots, and logs.
- Telemetry forbids query values, IPs, source IDs/text, contacts, usernames, session IDs,
  and other unbounded labels; release/request correlation IDs are random/bounded and
  never authorization tokens.
- Pull-request code receives no deployment/write credentials. Monitoring remains on
  internal networks, with secrets supplied only by existing atomic deployment transfer.
- Image/security exception entries require exact identity, owner, reason, expiry, and a
  test ensuring unrelated findings remain visible.

## Rollout and rollback

- T1/T2/T3/T4/T5/T7 are code/test/tooling changes with no product-data migration; roll
  back to the prior image/commit if characterization or health checks regress.
- T8 first observes/builds evidence in PR CI, then becomes release-blocking only after a
  green negative/positive proof. The previous digest-addressed release remains rollback.
- T6 deploys monitoring services disabled from public ingress, validates resource limits,
  scrapes, retention, alert fire/recover, and application failure isolation before
  enabling the owner alert route. Rollback stops/removes only E14 monitoring services
  and restores the previous application image/config; local telemetry is not a backup.
- Capacity tests never target live production. Any topology/resource tuning derived from
  T7 is separately bounded in T7 and rolled back with the prior complete production config.
- No task mutates or deletes production data. E14-T9 recovery work requires a later plan.

## Risks and stop conditions

- A product/persisted contract, parser semantic, transaction boundary, auth/privacy rule,
  deployment ownership/topology beyond the selected monitoring slice, or new runtime
  dependency outside this list invalidates the plan before implementation continues.
- E8-T5 remaining non-`done` blocks T6 and therefore T7; it is not waived by this plan.
- The owner alert webhook secret is external operational input; T6 may land reviewed
  implementation but cannot become `done` until delivery/fire/recover evidence exists.
- E14-T9 remains blocked on ADR-015/E7-T5 and explicit recovery policy/credentials.
- Browser/image/security tooling may expose hosted-runner limits; preserve required
  evidence with a documented scheduled/manual split, never by treating missing checks as success.

## Approval request

Owner approval of implementation-plan revision 1 authorizes exactly E14-T1, T2, T3,
T4, T5, T8, T6, and T7 with the constraints and dependencies above. It does not approve
E14-T9, supersede ADR-015, complete E8-T5, supply an alert webhook, or waive one-task
branches, reviews, validation, required green CI, deployment health, or rollback gates.
