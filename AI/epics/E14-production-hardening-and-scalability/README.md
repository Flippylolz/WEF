---
schema: ai-workflow/epic@1
id: E14
title: "Production hardening and scalability"
status: planning
milestones: [M5]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E14: Production hardening and scalability

## Outcome

The live service has maintainable module boundaries, trustworthy automated checks,
measured capacity, user-centered reliability signals, hardened release artifacts,
and rehearsed recovery. Improvements are driven by evidence and explicit budgets,
not by speculative infrastructure or framework rewrites.

## Why this is E14

E11 is already the completed **Scalable quick filters** epic, E12 is the completed
**Database index audit** epic, and E13 is the completed **Dark map-first explorer**
established in PR #174. This post-launch initiative therefore uses E14 so the
independently reviewable workstreams retain distinct identifiers.

## Approval state

- Epic workspace: `planning` after the owner approved spike revision 1 on 2026-08-29.
- [Research spike](SPIKE.md): revision 1, owner-approved under AD-041.
- [Implementation plan](IMPLEMENTATION_PLAN.md): revision 1, `awaiting_approval`;
  implementation remains prohibited until its separate owner decision.
- E14-T1 through E14-T8 are promoted/`draft`; E14-T9 remains proposed and
  non-actionable behind ADR-015/E7-T5.

## Audit baseline

The spike surveyed the repository on 2026-08-26 and was revalidated against
up-to-date `origin/main` at `d0b6635` on 2026-08-27, covering application code,
tests, contracts, CI, deployment, security, operations, and workflow documentation.

Strong existing foundations include strict Python/TypeScript checks, 17 backend
import contracts, deterministic OpenAPI drift checks, container hardening,
deployment rollback proofs, 90% per-suite coverage floors, and synthetic-data
privacy controls. The principal residual risks are:

- no backup/restore guarantee while [ADR-015](../../decisions/adr/ADR-015-defer-backups.md)
  and [E7-T5](../E7-production-delivery/proposed-tasks/E7-T5-future-backup-and-restore-capability.md)
  remain deferred;
- aggregate coverage hiding critical adapters with materially lower coverage;
- one mocked, Chromium-only Playwright suite with the map disabled and no real
  browser-to-API-to-PostGIS path;
- large orchestration hotspots in the frontend, ingestion persistence/extraction,
  operator commands, and deployment proof scripts;
- no production SLO/error-budget model, metrics backend, actionable alert loop, or
  persisted Web Vitals sink;
- no repeatable capacity/load envelope or enforced frontend bundle budget;
- dependency audits without a complete image/SBOM/release-integrity gate; and
- workflow/architecture documentation that can drift from executable CI and the
  implemented system.

## Planned task sequence

1. [E14-T1: Make quality and governance gates truthful](tasks/E14-T1-make-quality-and-governance-gates-truthful.md) — P1/M
2. [E14-T2: Strengthen critical-path test confidence](tasks/E14-T2-strengthen-critical-path-test-confidence.md) — P1/L; depends on T1
3. [E14-T3: Refactor frontend orchestration hotspots](tasks/E14-T3-refactor-frontend-orchestration-hotspots.md) — P1/L; depends on E13-T3/T2
4. [E14-T4: Refactor backend ingestion and operator seams](tasks/E14-T4-refactor-backend-ingestion-and-operator-seams.md) — P1/L; depends on T2
5. [E14-T5: Add full-stack cross-browser and accessibility journeys](tasks/E14-T5-add-full-stack-cross-browser-and-accessibility-journeys.md) — P1/L; depends on T3/T4
6. [E14-T8: Harden supply-chain and release integrity](tasks/E14-T8-harden-supply-chain-and-release-integrity.md) — P1/L; depends on T1
7. [E14-T6: Define SLOs and ship privacy-safe observability](tasks/E14-T6-define-slos-and-ship-privacy-safe-observability.md) — P1/L; depends on E8-T5/T1
8. [E14-T7: Prove capacity and enforce performance budgets](tasks/E14-T7-prove-capacity-and-enforce-performance-budgets.md) — P1/L; depends on T3/T4/T6
9. [E14-T9: Rehearse operational resilience and disaster recovery](proposed-tasks/E14-T9-rehearse-operational-resilience-and-disaster-recovery.md) — P0/L; depends on E7-T5/T6/T7/T8

The pending implementation plan sequences T8 before T6 so all work independent of
E8-T5 can finish before that external dependency gate. T9 remains outside plan
revision 1 and is the later terminal recovery-evidence task.

## Required check matrix

Every task runs the global definition of done plus the following task-specific
checks. A check must fail closed: missing evidence is not success.

| Task | Required evidence/checks |
| --- | --- |
| T1 | format, lint with zero warnings, strict types, backend architecture contracts and negative probe, unit/integration suites, OpenAPI drift/compatibility, Markdown links, CI/check-name consistency negative probe |
| T2 | per-suite coverage floors, critical-module floors, warning-free tests, deterministic repeat runs, representative mutation/negative probes for auth/contact/ingestion/catalog behavior |
| T3 | behavior-characterization tests, component/hook tests, axe checks, strict type/lint, production build, bundle-diff budget, no duplicated backend business rules |
| T4 | unit/integration/architecture tests, replay/idempotency/concurrency/cancellation/error-redaction cases, migration compatibility where persistence changes, operator exit-code proofs |
| T5 | real full-stack Playwright journeys, Chromium/Firefox/WebKit, desktop/mobile, WebGL-enabled Chromium map smoke, auth/contact/favorites/error/keyboard flows, axe scan, trace/screenshot artifacts on failure |
| T6 | SLI schema/cardinality/redaction tests, frontend field-vitals delivery, API/worker/database/edge telemetry, alert fire-and-recover rehearsal, runbook and incident-template review |
| T7 | versioned representative dataset, API p50/p95/p99 and error rate, SQL query/plan budgets, pool/saturation evidence, ingestion catch-up rate, frontend bundle/Lighthouse budgets, repeatability envelope |
| T8 | dependency-diff review, source/secret scan, locked dependency audits, image vulnerability scan, SBOM tied to both image digests, previous-release migration/startup proof, release-manifest verification |
| T9 | encrypted off-host backup freshness, database/media/config restore into isolation, checksum/reconciliation proof, measured RPO/RTO, failure injection and alerting, documented failover/rollback decision |

## Cross-epic recovery gate

E14 does not duplicate E7-T5. Because the product is live, the owner should review
ADR-015 immediately and either:

1. approve superseding the deferral and promote/refine E7-T5 as a P0 prerequisite
   for E14-T9; or
2. explicitly re-accept the single-host total-data-loss risk with a review date.

Until that decision is recorded, E14-T9 remains blocked and no document may claim
that persistence or deploy rollback is a backup.

## Scope controls

- Refactor incrementally behind characterization tests; no big-bang rewrite.
- Preserve the backend-authoritative business model and current modular-monolith
  topology until measured thresholds justify a change.
- No Kubernetes, Redis, queue, replica, CDN, SaaS telemetry, or production
  dependency is pre-approved by this epic.
- No raw source data, contacts, credentials, session material, or production
  telemetry payloads enter Git or test fixtures.
- New tooling/dependencies require explicit approval in the implementation plan.
