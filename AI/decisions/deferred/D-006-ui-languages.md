---
schema: ai-docs/deferred-decision@1
id: D-006
title: UI languages
status: resolved
task_gates: []
resolved_by: [product/QUALITY]
---

# D-006: UI languages

- Status: resolved for the initial release by the canonical [Product Quality language section](../../product/QUALITY.md#language). The `product/QUALITY` resolver is a canonical document key, not an ADR or deferred-decision ID.
- English is the default UI language.
- Every user-facing string is an i18n key; Polish/Russian/Ukrainian translations are deferred.
- Source text preserves its language while applying server-side contact masking.
