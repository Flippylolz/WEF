---
schema: ai-docs/adr@1
id: ADR-009
title: Use protected-main feature-branch development
status: accepted
date: 2026-08-12
supersedes: []
superseded_by: [ADR-017]
resolves: []
---

# ADR-009: Use protected-main feature-branch development

- Status: feature-branch/PR workflow accepted; enforced protection superseded by [ADR-017](ADR-017-no-enforced-branch-protection.md)
- Date: 2026-08-12
- Decision: `https://github.com/Flippylolz/WEF` is the canonical repository. Every feature/change uses its own branch and pull request; ordinary merges require lint/tests and deployment verifies a merged-PR-associated `main` SHA. [ADR-017](ADR-017-no-enforced-branch-protection.md) later removed platform-enforced protection.
- Rationale: small independently reviewed changes make parser, schema, and deployment risk easier to control.
- Consequence: direct ordinary pushes remain procedurally forbidden but are not platform-blocked under [ADR-017](ADR-017-no-enforced-branch-protection.md). Only the owner may authorize an audited `hotfix/*` emergency. Dependabot's custom controller merges patch/minor updates only after expected checks pass.
