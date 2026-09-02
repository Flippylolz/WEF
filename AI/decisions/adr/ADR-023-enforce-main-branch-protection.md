---
schema: ai-docs/adr@1
id: ADR-023
title: Enforce main branch protection
status: accepted
date: 2026-09-02
supersedes: [ADR-017]
superseded_by: []
resolves: []
---

# ADR-023: Enforce main branch protection

- Status: accepted and applied
- Date: 2026-09-02
- Decision: protect `main` with GitHub's branch-protection API now that the public repository is eligible. Require a pull request, one approval, stale-review dismissal, approval after the latest reviewable push, resolved review conversations, strict successful CI, and linear history. Block force pushes and deletion. Keep repository-administrator enforcement disabled only for the owner emergency/bootstrap exception described in repository governance.
- Required checks: `Backend`, `Frontend and contract`, `Repository safety`, `Runtime images`, and `Coverage badge`.
- Rationale: platform enforcement now provides a safer default than the procedural-only controls accepted while the private repository was ineligible.
- Consequence: ordinary contributors and automation cannot update `main` unless the protected pull-request and CI gates pass. The merged-PR deployment check remains defense in depth. Administrator bypasses remain exceptional, audited, and subject to post-merge CI and rollback requirements.
- Supersedes: [ADR-017](ADR-017-no-enforced-branch-protection.md).
