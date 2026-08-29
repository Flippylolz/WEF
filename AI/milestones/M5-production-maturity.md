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

- E17-T1 through E17-T6, all currently non-actionable proposed tasks.
- Completion is owner-gated: E17 is `done` only after the owner supplies a new data
  backup that is replayed and promoted to production (E17-T6).

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
