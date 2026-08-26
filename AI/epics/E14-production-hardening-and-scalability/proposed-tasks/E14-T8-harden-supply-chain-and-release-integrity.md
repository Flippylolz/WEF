---
schema: ai-workflow/proposed-task@1
id: E14-T8
epic: E14
title: "Harden supply-chain and release integrity"
status: proposed
revision: 1
actionable: false
priority: P1
size: L
milestone: M5
dependencies: [E14-T1]
requirement_ids: [P-007, P-008]
decision_ids: [ADR-008, ADR-009, ADR-013, ADR-014, ADR-017]
deferred_decision_ids: []
source: "repository-audit:2026-08-26"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E14-T8: Harden supply-chain and release integrity

## Outcome

Every deployed backend/web image is traceable to reviewed source and locked inputs,
has an inspectable SBOM and vulnerability result tied to its digest, and is proven to
migrate/start from the previous supported release without leaking build secrets.

## Scope

- Verify plan eligibility for GitHub-native dependency review, code scanning, secret scanning, and attestations; choose available fail-closed alternatives where unavailable.
- Review dependency diffs/licenses on pull requests in addition to end-state `pip-audit`/`pnpm audit`.
- Generate SPDX or CycloneDX SBOMs for final backend/web runtime images and bind/store them with image digest/release manifest.
- Scan final runtime images, base OS packages, and application dependencies with severity policy, exact allowlist expiry/owner/reason, and negative probes.
- Verify source/action/base-image pins and that build caches/layers/artifacts contain no credentials, source exports, sessions, private media, or production config.
- Add previous-supported-release database migration plus new-image startup/health/compatibility proof; document rollback when schema changes are not backward compatible.
- Preserve least-privilege workflow permissions and digest-addressed deployment.

## Out of scope

- Assuming paid/private-repository GitHub features, automatic production dependency upgrades outside existing governance, signing keys without an approved custody model, or claiming zero vulnerabilities.

## Acceptance criteria and checks

- [ ] Every dependency-changing PR gets an available fail-closed vulnerability/license/diff review.
- [ ] Backend and web final image digests each have an SBOM, scanner result, source SHA, base digest, and release-manifest link.
- [ ] High/critical policy failures block release; exceptions are exact, time-bounded, owned, and do not hide unrelated findings.
- [ ] Negative probes prove a vulnerable fixture/image, missing SBOM, changed digest, unpinned action/base, or secret-bearing layer is rejected.
- [ ] A database at the previous supported revision migrates under the new release and the new app passes readiness/contract/smoke checks; rollback limits are explicit.
- [ ] Workflow permissions remain minimal and pull-request code never receives deployment/write credentials.
- [ ] Dependency review/audits, image/SBOM scan, release-manifest verification, migration/startup compatibility, secret/source exclusion, and runtime-content checks pass.

## Dependencies and gates

Depends on E14-T1 so required release checks cannot drift silently.

## Risks and notes

GitHub documents artifact attestations for private repositories as an Enterprise Cloud
feature. The plan must verify current eligibility and must not weaken integrity if it is unavailable.

## Promotion checklist

- [ ] E14 spike is explicitly owner-approved at its current revision.
- [ ] Scope, checks, dependencies, priority/size, and traceability match the approved spike.
- [ ] This file will be moved—not copied—to `tasks/` with complete promotion metadata.
