---
schema: ai-docs/adr@1
id: ADR-003
title: Do not infer current availability
status: accepted
date: 2026-08-12
supersedes: []
superseded_by: []
resolves: []
---

# ADR-003: Do not infer current availability

- Status: accepted
- Date: 2026-08-12
- Decision: show the source publication date and describe records as imported offers, not as currently available.
- Rationale: the export has no reliable sold, withdrawn, or active field.
- Consequence: map copy, API fields, and metadata must avoid an `available=true` default. A later authoritative status can be added without rewriting source history.
