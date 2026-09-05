---
id: M5
title: "Production maturity"
status: planned
---

# M5: Production maturity

## Outcome

The live service is maintainable, measurably reliable at its intended load, secure in
its release supply chain, observable without leaking personal data, and recoverable
from loss of the production host.

## Included epic/task definitions

### [E14: Production hardening and scalability](../epics/E14-production-hardening-and-scalability/README.md)

- E14-T1 through E14-T8 are promoted/`draft` under approved spike revision 1 while
  implementation plan revision 1 awaits owner approval; E14-T9 remains proposed/blocked.
- Existing E7-T5 is the recovery-capability prerequisite for E14-T9 and is not duplicated.

### [E17: Raw archive replay and filter integrity](../epics/E17-raw-archive-replay-and-filter-integrity/README.md)

- E17-T1 through E17-T6 — `done` through green-CI PRs #203/#208/#200/#201/#209/#211.
- Owner backup replay and production promotion completed 2026-08-30 (release
  `7a3e927`, deploy run 33280067325).

### [E18: Owner location management and verification](../epics/E18-owner-location-verification/README.md)

- E18-T1 and E18-T2 — `done` through green-CI PRs #217/#218 with verified deploys
  on 2026-08-30.

### [E19: AI-assisted owner catalog curation](../epics/E19-ai-assisted-place-curation/README.md)

- E19-T1 through E19-T4 — `done` through PRs #226–#230.

### [E20: Admin console visual refresh](../epics/E20-admin-console-visual-refresh/README.md)

- E20-T1 and E20-T2 — `done` through green-CI PRs #247/#254 with a verified
  production deploy on 2026-08-31 (deploy run 33429448184; `/admin` serving
  the dark Primer-aligned console, health live/ready 200).

## September 2026 audit follow-up

The [system audit](../audits/2026-09-05-system-audit.md) records passing suites plus production defects and defines the following selected research workspaces:

- [E24: Automatic ingestion recovery](../epics/E24-automatic-ingestion-recovery/README.md) — four proposed tasks; terminate stuck archive work, maintain monotonic cursors, recover media, and verify progress.
- [E25: Parser quality and automatic recovery](../epics/E25-parser-quality-and-automatic-recovery/README.md) — spike and implementation plan revision 1 approved; T1 implemented/validated locally with publication approval pending, and T2–T4 dependency-gated; benchmark source evidence, repair deterministic gaps, automate validated AI exceptions, and converge parser versions.
- [E26: Automatic location validation and repair](../epics/E26-automatic-location-validation/README.md) — three proposed tasks; validate address agreement, repair stale points, and present honest precision.
- [E27: Faster verified releases](../epics/E27-faster-verified-releases/README.md) — three proposed tasks; measure outcomes, remove duplicate serialized work safely, and prove the latency/recovery budget.

E14 continues to own shared quality gates, browser infrastructure, general refactoring, observability, and capacity. The new candidates do not duplicate completed work or change existing approval records. Their spikes await owner approval and implementation plans remain empty draft shells. The owner's operating requirement is automatic routine recovery with manual work only for exceptional unresolved cases.

## Exit evidence

- [ ] Quality, contract, architecture, and governance checks are truthful and fail closed.
- [ ] Critical logic has risk-weighted tests and real cross-browser/full-stack journeys.
- [ ] Maintainability hotspots are decomposed without changing business behavior.
- [ ] SLOs, capacity budgets, alerts, and incident procedures have rehearsed evidence.
- [ ] Release images have reviewed dependency/image/SBOM/migration integrity evidence.
- [ ] An isolated restore proves complete database/media/config recovery within approved RPO/RTO.
- [ ] Every required task is promoted, approved, dependency-gated, implemented on its dedicated branch, and completed with definition-of-done evidence.

## Status rule

`planned` grants no implementation permission. M5 becomes `done` only when all exit
evidence and task completion records satisfy the approval-gated workflow.
