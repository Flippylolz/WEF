---
schema: ai-workflow/proposed-task@1
id: E14-T6
epic: E14
title: "Define SLOs and ship privacy-safe observability"
status: proposed
revision: 1
actionable: false
priority: P1
size: L
milestone: M5
dependencies: [E8-T5, E14-T1]
requirement_ids: [P-001, P-006, P-007, P-008]
decision_ids: [ADR-006, ADR-008, ADR-010, ADR-014, ADR-015]
deferred_decision_ids: []
source: "repository-audit:2026-08-26"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E14-T6: Define SLOs and ship privacy-safe observability

## Outcome

Operators can detect and diagnose user-impacting failures through approved SLIs/SLOs,
bounded privacy-safe telemetry, actionable alerts, and rehearsed incident procedures;
frontend Web Vitals reach an owned sink instead of being discarded.

## Scope

- Define measured availability, latency, error, freshness, and critical-journey SLIs with windows, exclusions, percentiles, and initial SLO/error-budget policy.
- Instrument API/edge/database/worker golden signals and ingestion lag/reconciliation without high-cardinality or personal-data labels.
- Deliver sampled frontend Core Web Vitals and client errors to an approved same-origin or reviewed external sink with consent/retention decisions documented.
- Correlate release/request/run identifiers across logs, metrics, and traces where selected.
- Add external black-box checks and alerts for public health/critical paths, worker staleness/gaps, disk pressure, certificate expiry, backup freshness once E7-T5 exists, and repeated deploy failure.
- Write alert ownership, severity, silence/escalation, incident, rollback, and postmortem runbooks; fire and recover every required alert in a safe rehearsal.

## Out of scope

- A preselected SaaS/vendor, logging source/contact values, unlimited retention/cardinality, paging for non-actionable symptoms, or claiming backup coverage before E7-T5.

## Acceptance criteria and checks

- [ ] Every SLI names the user outcome, source, aggregation/window, percentile, objective, exclusions, and response when the error budget is exhausted.
- [ ] Metrics/traces/logs carry bounded labels and pass negative redaction/cardinality tests for contacts, source text, credentials, sessions, query values, IPs, and unbounded IDs.
- [ ] Production Web Vitals and approved client errors reach a tested sink with sampling, retention, failure isolation, and no impact on page use.
- [ ] Dashboards answer release health, API latency/errors, DB saturation, worker freshness/gaps, disk/certificate state, and deployment status.
- [ ] Each required alert is symptom-based, actionable, owned, linked to a runbook, and proven to fire then recover in rehearsal.
- [ ] Telemetry outage does not break the application or worker.
- [ ] Unit/integration/redaction/cardinality/exporter-failure, alert-rehearsal, dashboard/runbook, and production smoke checks pass.

## Dependencies and gates

Depends on E8-T5 for final worker signals and E14-T1 for truthful gates.

## Risks and notes

The implementation plan must compare host resource/cost, privacy, retention, and
operational burden before approving any backend or vendor.

## Promotion checklist

- [ ] E14 spike is explicitly owner-approved at its current revision.
- [ ] Scope, checks, dependencies, priority/size, and traceability match the approved spike.
- [ ] This file will be moved—not copied—to `tasks/` with complete promotion metadata.
