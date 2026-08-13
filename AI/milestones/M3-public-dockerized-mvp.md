---
id: M3
title: "Public Dockerized MVP"
status: in_progress
---

# M3: Public Dockerized MVP

## Outcome

The responsive map experience is production-deployed from GitHub with persistent server storage, monitoring, application rollback, attribution, contact masking, and reveal auditing. An interim anonymous-only HTTP rehearsal may precede launch; M3 public launch includes E7-T7 HTTPS before registration/contact reveal/admin is enabled. Backups remain explicitly out of scope.

## Current constraints

- Only the configured edge port is published, and the existing NUC workloads must remain unchanged.
- Production authentication, administration, and contact reveal remain disabled until HTTPS and required secrets pass smoke/security checks.
- Rollback covers compatible application releases; no destructive schema downgrade or data-recovery guarantee is implied.
- E7-T5 remains deferred under ADR-015 and is not a public-launch gate.

## Included epic/task definitions

### [E5: Interactive map frontend](../epics/E5-interactive-map-frontend/README.md)

- [E5-T3: Build offer detail and media gallery](../epics/E5-interactive-map-frontend/proposed-tasks/E5-T3-build-offer-detail-and-media-gallery.md) — `proposed`
- [E5-T4: Complete responsive list/map accessibility](../epics/E5-interactive-map-frontend/proposed-tasks/E5-T4-complete-responsive-list-map-accessibility.md) — `proposed`
- [E5-T5: Performance and production UX pass](../epics/E5-interactive-map-frontend/proposed-tasks/E5-T5-performance-and-production-ux-pass.md) — `proposed`
### [E6: Quality, security, and operations](../epics/E6-quality-security-operations/README.md)

- [E6-T1: Complete automated test pyramid](../epics/E6-quality-security-operations/proposed-tasks/E6-T1-complete-automated-test-pyramid.md) — `proposed`
- [E6-T2: Perform privacy and security hardening](../epics/E6-quality-security-operations/proposed-tasks/E6-T2-perform-privacy-and-security-hardening.md) — `proposed`
- [E6-T3: Add operational diagnostics](../epics/E6-quality-security-operations/proposed-tasks/E6-T3-add-operational-diagnostics.md) — `proposed`
- [E6-T4: Implement in-house registration and sessions](../epics/E6-quality-security-operations/proposed-tasks/E6-T4-implement-in-house-registration-and-sessions.md) — `proposed`
- [E6-T5: Implement contact masking, encryption, reveal, and audit](../epics/E6-quality-security-operations/proposed-tasks/E6-T5-implement-contact-masking-encryption-reveal-and-audit.md) — `proposed`
- [E6-T6: Implement English i18n and restricted-action UX](../epics/E6-quality-security-operations/proposed-tasks/E6-T6-implement-english-i18n-and-restricted-action-ux.md) — `proposed`
- [E6-T7: Implement owner administration console](../epics/E6-quality-security-operations/proposed-tasks/E6-T7-implement-owner-administration-console.md) — `proposed`
### [E7: Docker/GitHub production delivery](../epics/E7-production-delivery/README.md)

- [E7-T1: Build production Compose topology](../epics/E7-production-delivery/tasks/E7-T1-build-production-compose-topology.md) — `in_progress`, stacked on E5-T1/E1-T3
- [E7-T2: Provision and verify supplied server](../epics/E7-production-delivery/tasks/E7-T2-provision-and-verify-supplied-server.md) — `in_progress`, stacked on E7-T1
- [E7-T3: Implement GitHub image and deployment workflows](../epics/E7-production-delivery/tasks/E7-T3-implement-github-image-and-deployment-workflows.md) — `in_progress`, stacked on E7-T2
- [E7-T4: Implement health verification and rollback](../epics/E7-production-delivery/tasks/E7-T4-implement-health-verification-and-rollback.md) — `in_progress`, stacked on E7-T3
- [E7-T5: Future backup and restore capability](../epics/E7-production-delivery/proposed-tasks/E7-T5-future-backup-and-restore-capability.md) — `deferred`
- [E7-T6: Transfer and import the historical dataset](../epics/E7-production-delivery/proposed-tasks/E7-T6-transfer-and-import-the-historical-dataset.md) — `proposed`
- [E7-T7: Enable production registration and contact reveal](../epics/E7-production-delivery/proposed-tasks/E7-T7-enable-production-registration-and-contact-reveal.md) — `proposed`

Cancelled and deferred candidates remain linked for traceability but are not completion requirements unless an approved revision restores them to required scope.

## Exit evidence

- [ ] Responsive map/list/detail and restricted-action flows satisfy accessibility, privacy, security, and performance evidence.
- [ ] Immutable images deploy from GitHub to the isolated NUC topology with complete validated configuration and no host interference.
- [ ] Health verification and compatible application rollback are rehearsed; release SHA/digests/migration revision are auditable.
- [ ] HTTPS-gated registration, owner administration, and contact reveal pass production smoke/security checks while anonymous browsing remains available.
- [ ] Every required task has been promoted, approved, dependency-gated, implemented on its dedicated branch, and completed with definition-of-done evidence.

## Status rule

`in_progress` records the approved anonymous production-rehearsal sequence only; it grants no permission for still-proposed public-launch tasks. Change this milestone to `done` only when all required exit evidence and task completion records exist under the [workflow](../workflow/README.md).
