---
schema: ai-docs/adr@1
id: ADR-017
title: Operate without enforced GitHub branch protection
status: accepted
date: 2026-08-12
supersedes: [ADR-009]
superseded_by: []
resolves: [D-007]
---

# ADR-017: Operate without enforced GitHub branch protection

- Status: accepted for current scope
- Date: 2026-08-12
- Decision: GitHub Pro and private-repository rulesets are completely out of scope. Continue feature/spike/fix branches, pull requests, CI, main-only deploy checks, and the custom Dependabot merge controller as workflow conventions without claiming GitHub-enforced `main` protection.
- Rationale: the owner explicitly accepts the missing enforcement.
- Consequence: an administrator can bypass checks or push directly, so repository governance is procedural rather than guaranteed. E1-T5 is cancelled unless scope changes.
- Supersedes: [ADR-009](ADR-009-feature-branch-development.md) only where it claimed direct pushes and failing merges were technically blocked.
- Resolves: [D-007](../deferred/D-007-github-protection-eligibility.md).
