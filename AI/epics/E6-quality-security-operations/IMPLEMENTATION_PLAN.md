---
schema: ai-workflow/implementation-plan@1
epic: E6
title: "Quality, security, and operations implementation plan"
status: approved
revision: 3
owner: owner
spike_revision: 2
task_sequence:
  - id: E6-T5
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-20T10:40:42Z"
  approved_revision: 3
  evidence: "Owner continue / autonomous epic mission directive (AD-009); E4-T3 and E6-T4 are done on main, unblocking E6-T5 while E7-T10 remains gated by D-009"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: E6-T5 contact masking, encryption, reveal, and audit

## Approved spike baseline

- [Spike revision 2](SPIKE.md) remains owner-approved and current.
- Binding decisions: [ADR-011](../../decisions/adr/ADR-011-accounts-gate-contact-reveal.md), [ADR-012](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md), [ADR-016](../../decisions/adr/ADR-016-pseudonymous-accounts-owner-console.md); security contract [AUTH_ADMIN_CONTACTS](../../security/AUTH_ADMIN_CONTACTS.md); data model `ContactPoint` / `ContactReveal` in [DATA_MODEL](../../contracts/DATA_MODEL.md).
- E0 spike locks `cryptography` for authenticated contact encryption/HMAC primitives; adding that production dependency is in-scope for this plan (no alternate crypto library).

## Scope and outcome

Deliver server-side contact persistence and the authenticated no-store reveal mutation so anonymous map/detail/source responses never contain raw phones/handles, while active accounts can reveal only contacts for publicly visible offers under rate limits and minimized audit. Production enablement of registration/reveal remains [E7-T7](../E7-production-delivery/proposed-tasks/E7-T7-enable-production-registration-and-contact-reveal.md) after HTTPS.

## Ordered task sequence

1. [E6-T5: Implement contact masking, encryption, reveal, and audit](tasks/E6-T5-implement-contact-masking-encryption-reveal-and-audit.md) — revision 1.
   - Independently reviewable: new `contacts` feature (or equivalent modular slice), additive `contact_points` / `contact_reveals` migration, ingestion persist of encrypted contacts + masked public text, `POST /api/v1/offers/{offer_id}/contacts/reveal`, OpenAPI + frontend codegen, unit/integration/security tests.
   - Dependencies: E2-T2, E3-T1, E4-T3, E6-T4 — all `done` on integrated main.
   - Affected modules/contracts: `features/contacts/` (or co-located ports under catalog/identity per import-linter), ingestion persistence adapter, composition/settings secrets, Alembic head, `contracts/openapi/v1.json`, `apps/web/src/generated/api.ts`, AUTH_ADMIN_CONTACTS/DATA_MODEL alignment notes if needed.
   - Tests: masking fixtures; AES-GCM encrypt/decrypt + HMAC fingerprint stability; reveal authz (anonymous/disabled/forced-change/IDOR/rate-limit); audit minimization (no plaintext/IP/UA); OpenAPI additive-only; no secret leakage in logs.
   - Migration: additive tables; `EXPECTED_DATABASE_REVISION` advances; rollback is redeploy-previous (unused tables remain).
   - Secrets: `WEF_CONTACT_ENCRYPTION_KEY` and `WEF_CONTACT_HMAC_KEY` (or equivalent) via settings; never committed; tests use ephemeral keys.

Only E6-T5 is sequenced. E6-T1/T2/T3/T6/T7 remain proposed until their own plan revisions.

## Cross-task architecture

- Reuse E6-T4 `_require_account`, origin/CSRF JSON guards, and `MemoryRateLimiter` patterns; authorization stays in application interactors.
- Reveal may call catalog visibility (same `OfferVisibility.VISIBLE` gate as offer detail); do not leak existence of non-visible offers beyond public masking.
- Ingestion already extracts `ContactSpan` and builds `source_text_public_masked`; this task materializes `ContactPoint` rows and keeps public APIs on masked text only.
- Frontend reveal UX is out of scope (E6-T6). Owner audit console is out of scope (E6-T7).

## Data and migrations

- One Alembic revision creating `contact_points` and `contact_reveals` per DATA_MODEL.
- Ciphertext + keyed fingerprint + safe `masked_value`; plaintext never indexed.
- Reveal audit outcomes: `allowed`, `rate_limited`, `forbidden`, `unavailable`.

## Security and privacy

- AES-GCM via `cryptography`; HMAC-SHA256 fingerprints with a distinct key.
- `Cache-Control: no-store, private` on reveal responses.
- Auth/reveal remain disabled on plain HTTP until E7-T7 (ADR-019 / ADR-011 production gate).
- Negative tests prove ciphertext/keys/plaintext never appear in public responses or structured logs.

## Test and verification strategy

- Pytest unit + PostGIS integration + contract export/codegen/oasdiff additive proof.
- CI remains the merge gate; no live production reveal activation.

## Operations, rollout, and rollback

- Migrate-then-serve via existing readiness revision gate.
- Configure contact keys in deployment secrets before E7-T7; until then the feature may refuse reveal safely when keys are absent.
- Rollback: previous image; additive tables unused.

## Risks and mitigations

- Missing keys in rehearsal: fail closed on encrypt/reveal; do not write plaintext.
- Scope creep to E6-T6/T7 or E7-T7: explicitly out of scope.
- Dependency on historical contact density: synthetic and fixture offers cover acceptance; full historical backfill of contact_points may occur on next import/replay without blocking API merge.

## Invalidation triggers

- Material change to reveal authorization, encryption algorithm, or public contact contracts.
- New deferred decision blocking contact storage.
- Re-scope that merges owner console or frontend reveal UX into this task.

## Approval checklist

- [x] The referenced spike revision has explicit owner approval and remains valid.
- [x] Every sequence entry is a promoted task with complete acceptance criteria and traceability.
- [x] Dependencies are complete, acyclic, and enforceable task by task.
- [x] Affected modules, contracts, tests, migrations, risks, rollout, and rollback are explicit.
- [x] Deferred decisions required for implementation are resolved (none for E6-T5).
- [x] No production or disposable proof code has been written in this plan PR.
- [x] `revision` represents the material plan being submitted.
- [x] Approval recorded under the owner continue / AD-009 autonomous directive.

## Owner decision

The owner records the decision only in the YAML `approval` object. Approval authorizes this plan revision, not blanket epic implementation: E6-T5 still requires promotion, dependency, branch, and evidence gates.
