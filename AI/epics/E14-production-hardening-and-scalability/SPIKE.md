---
schema: ai-workflow/spike@1
epic: E14
title: "Production hardening and scalability audit"
status: awaiting_approval
revision: 1
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-003, ADR-004, ADR-005, ADR-006, ADR-007, ADR-008, ADR-009, ADR-010, ADR-012, ADR-013, ADR-014, ADR-015, ADR-016, ADR-017, ADR-021]
domain_docs: [architecture, product, contracts, ingestion, security, operations, governance, workflow]
proposed_task_ids: [E14-T1, E14-T2, E14-T3, E14-T4, E14-T5, E14-T6, E14-T7, E14-T8, E14-T9]
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

# Spike: Production hardening and scalability audit

> This spike is documentation and research only. It does not authorize code,
> configuration, infrastructure, dependency, migration, or production changes.

## Question

Which bounded improvements give the live WEF system the largest gains in
maintainability, test confidence, scalability, security, observability, and
recoverability without rewriting proven architecture or adding speculative
infrastructure?

## Context and constraints

- The target remains fewer than 10,000 users on one modest Linux host, scaling
  vertically until measured evidence reaches a documented trigger.
- Backend business behavior, authorization, projections, and ingestion semantics
  remain authoritative; frontend refactors may not duplicate them.
- Production already uses immutable digest-addressed images, health-gated rollout,
  hardened Compose services, deterministic contracts, and rollback proofs.
- Backups are explicitly deferred by ADR-015. This is the highest-severity residual
  production risk and cannot be described as solved by persistence or release rollback.
- Mainline is actively changing through E8 and E13. Findings tied to a transient dirty
  checkout are distinguished from findings verified on `origin/main`.
- New production dependencies/services need owner approval. Tool names in candidate
  tasks describe capabilities unless the implementation plan explicitly selects one.

## Research method

- Read-only repository survey on 2026-08-26 of `apps/backend`, `apps/web`, `scripts`,
  `infra`, `.github`, `contracts`, and governing `AI/` documents, revalidated on
  2026-08-27 after E13-T1 and the implementation-state documentation sync landed on
  `origin/main` at `d0b6635`.
- Static inventory of source/test file counts, large modules, suppressions, test
  distribution, database access, runtime limits, security headers, and CI jobs.
- Execution of the repository's format, lint, architecture, strict-type, backend,
  and frontend test commands against the active checkout and an isolated up-to-date
  `origin/main` worktree.
- Review of authoritative upstream guidance: PostgreSQL 17
  [continuous archiving/PITR](https://www.postgresql.org/docs/17/continuous-archiving.html),
  Google SRE [service-level objectives](https://sre.google/sre-book/service-level-objectives/),
  Playwright [browser projects](https://playwright.dev/docs/browsers), Next.js
  [production checklist](https://nextjs.org/docs/app/guides/production-checklist),
  OpenTelemetry [Python instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/),
  GitHub [dependency review](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/manage-your-dependency-security/configure-dependency-review-action),
  and GitHub [artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations).

## Evidence baseline

### Existing strengths

- Backend: 142 Python source files, 52 test files, 405 passing tests, 90.69% branch-aware
  coverage, strict mypy, Ruff `ALL`, and 17 passing import-linter contracts.
- Frontend: 52 non-generated TypeScript/TSX source files, 24 test files, 130 passing
  tests, 94.93% statements and 90.86% branches, strict TypeScript, ESLint, Prettier,
  Testing Library, axe, and Playwright.
- CI checks deterministic OpenAPI generation, breaking contract changes, locked
  dependencies, production builds, dependency advisories, Markdown links, Compose
  topology, non-root/minimal images, source exclusions, and deployment proofs.
- Production Compose applies read-only filesystems, dropped capabilities,
  no-new-privileges, tmpfs, CPU/memory/PID limits, health checks, log rotation,
  isolated networks, and digest-addressed images.

### Verified gaps

1. **Recovery:** ADR-015 accepts total loss of PostgreSQL, media, imports, and local
   secrets if the single host fails. E7-T5 is only a deferred P2 candidate, despite
   the service now being live. PostgreSQL's own documentation states valuable
   databases should be backed up regularly and describes PITR from base backups plus WAL.
2. **Coverage signal quality:** the global backend floor passes while critical files
   are much lower, including `import_command.py` at 35%, favorite persistence at 39%,
   the pending-geocode adapter at 46%, recurring command at 59%, offer detail adapter
   at 63%, complete-import repository at 67%, and dry-run domain at 69%.
3. **Browser confidence:** the only E2E spec contains three catalog journeys, mocks all
   `/api/v1/*` responses, runs Chromium only, and builds with the map canvas disabled.
   It cannot detect browser/API/schema/database/migration wiring defects or WebKit/
   Firefox regressions. Playwright supports Chromium, Firefox, WebKit, and device projects.
4. **Accessibility depth:** axe covers only the initial explorer shell. Modal, gallery,
   authenticated contact reveal, favorites, error recovery, mobile sheets, and real
   keyboard journeys lack browser-level accessibility evidence.
5. **Maintainability hotspots:** after E13-T1, `map-explorer.tsx` is 903 lines and its
   test is 991; `globals.css` is 1,477; `account-modal.tsx` is 543; ingestion extraction
   is 809; ingestion persistence is 756; `import_command.py` is 683; multiple production
   proof/controller scripts are 500–749 lines with broad lint suppressions. Size alone
   is not a defect, but these files combine state/orchestration, transport, persistence,
   rendering, or proof logic and create high change fan-in.
6. **Observability:** structured logs and diagnostics exist, but no metrics/tracing
   backend, explicit SLI/SLO/error budget, or rehearsed alert loop exists. Web Vitals
   registers callbacks but the default sink is `null`, so production field data is
   discarded. Google SRE recommends user-centered SLIs and percentiles, with both
   server- and client-side indicators where needed.
7. **Capacity:** a local map latency test enforces 500 ms p95 on a representative query,
   but there is no concurrent workload, production-sized versioned dataset envelope,
   DB pool/saturation budget, ingestion catch-up measurement, frontend bundle budget,
   or repeatable capacity report.
8. **Rate-limit scaling:** public/auth/contact rate limits are in-process memory objects.
   Limits reset on restart and do not coordinate across processes. This is acceptable
   only while the one-process topology is explicit and must be revisited before adding
   workers/replicas.
9. **Supply chain:** dependencies are locked/audited and Actions/base images are pinned,
   but CI does not produce an SBOM per image, scan the final images as deployed, or
   enforce dependency-diff review. GitHub attestations are unavailable for this private
   repository on the documented current plan, so the plan must not assume that feature.
10. **Truth drift prevention:** PR #177 reconciled the known governance check-name and
    implemented-state documentation differences found by the initial audit. There is
    still no automated consistency check protecting these critical declarations from
    recurring drift.

The active dirty checkout initially failed frontend format/type/lint checks, but the
same fixes were already present in newer `origin/main` commits. The isolated mainline
worktree passed `make format-check`, `make lint`, and `make typecheck`; transient dirty
work was therefore not turned into a redundant task.

## Options considered

### A. Incremental evidence-led hardening on the modular monolith — recommended

Add characterization tests first, split only proven hotspots, define SLOs/capacity
budgets, close the real full-stack browser gap, harden build evidence, and restore from
off-host backups. This preserves working architecture and provides objective triggers
for future scale changes.

### B. Broad rewrite or premature distributed architecture — rejected

Splitting services, adding a queue/cache, or adopting orchestration before measured
pressure would increase failure modes, data-consistency burden, operating cost, and
test surface while leaving backup, alerting, and real journey gaps unresolved.

### C. Raise aggregate coverage and add more mocked tests only — rejected

The aggregate floors already pass. Raising one global number can incentivize low-value
tests and still miss real wiring, browser, concurrency, recovery, and operational failure
modes. Critical-module risk floors and full-stack journeys are more discriminating.

### D. Buy a managed observability/security platform immediately — deferred

A SaaS could shorten implementation, but it changes cost, privacy, retention, secrets,
and vendor dependencies. First define signals, redaction, cardinality, retention, and
operational response; the approved implementation plan may then compare self-hosted,
host-native, and managed options.

## Recommendation

Approve the nine-task incremental sequence in the epic README, with three controls:

1. Treat E7-T5/ADR-015 as an immediate owner decision and a hard dependency of the
   final recovery task; do not create a duplicate backup task in E14.
2. Complete E13-T3, then establish characterization and quality-gate truth before
   refactoring the same frontend seams; preserve behavior and architecture through
   small, independently reviewable changes.
3. Define user-centered reliability/capacity budgets before selecting observability
   or scaling infrastructure. Add components only when evidence crosses a trigger.

## Proposed task boundaries

- E14-T1 owns executable quality/governance truth, warnings, and consistency checks.
- E14-T2 owns risk-weighted test quality and critical-module confidence.
- E14-T3 owns frontend orchestration seams and bundle-aware maintainability.
- E14-T4 owns backend ingestion/operator seams and transaction/replay confidence.
- E14-T5 owns real full-stack browser and accessibility journeys.
- E14-T6 owns SLOs, privacy-safe telemetry, alerts, and incident response.
- E14-T7 owns repeatable capacity/load/plan/bundle budgets and scale triggers.
- E14-T8 owns dependency/image/SBOM/release/migration integrity.
- E14-T9 owns resilience failure injection and restored-backup evidence, depending on
  the existing E7-T5 recovery capability.

## Risks and open questions

- Owner decision: supersede or re-accept ADR-015; define initial RPO/RTO and acceptable
  encrypted off-host destination/cost.
- Observability selection must bound personal-data exposure, telemetry cardinality,
  retention, server resources, and recurring cost before any dependency is approved.
- Cross-browser/WebGL CI can be expensive or flaky; use a risk-based matrix and retain
  failure artifacts without weakening required critical journeys.
- Refactors can become feature rewrites; acceptance requires behavior-equivalence
  evidence and a bounded diff, not merely smaller files.
- Load fixtures must be synthetic/redacted yet representative enough to expose query,
  pool, payload, and ingestion bottlenecks.
- Private-repository plan limitations may rule out GitHub-native dependency review,
  CodeQL, or attestations; the plan must verify eligibility and select an available
  fail-closed alternative rather than silently omitting the control.

## Invalidation triggers

- Production moves away from the single-host modular-monolith topology.
- E8 materially changes ingestion concurrency, source count, or freshness semantics.
- The owner changes backup, privacy, data-retention, service-level, or budget policy.
- A major framework/runtime migration changes test, build, or instrumentation strategy.
- New evidence shows a proposed task is not independently reviewable or duplicates an
  active approved task in another epic.

## Exit checklist

- [x] The bounded question is answered within the stated scope.
- [x] Verified facts, transient checkout findings, assumptions, and uncertainty are distinguished.
- [x] Governing decisions and domain documents were reviewed.
- [x] Current authoritative upstream references support recovery, SLO, browser, frontend performance, telemetry, and supply-chain findings.
- [x] Proposed task boundaries, dependencies, checks, risks, and sequencing are identified.
- [x] No production or disposable proof code was created.
- [x] `revision` represents the material content submitted.
- [x] Status is `awaiting_approval` and approval remains `pending`.

## Owner decision

The owner records the decision only in the YAML `approval` object. Approval of spike
revision 1 permits task refinement/promotion and implementation planning; it does not
authorize implementation.
