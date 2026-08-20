---
schema: ai-workflow/task@1
id: E6-T5
epic: E6
title: "Implement contact masking, encryption, reveal, and audit"
status: ready
revision: 1
priority: P1
size: L
milestone: M3
dependencies: [E2-T2, E3-T1, E4-T3, E6-T4]
requirement_ids: [P-002, P-007, P-008]
decision_ids: [ADR-011, ADR-012, ADR-016]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E6-T5-implement-contact-masking-encryption-reveal-and-audit.md
  promoted_by: "Cursor Agent (autonomous epic mission)"
  promoted_at: "2026-08-20T10:42:05Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T10:42:05Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 3
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T10:42:05Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T10:42:05Z"
  evidence:
    - "E2-T2 | done | historical extractors live on main"
    - "E3-T1 | done | schema/migrations baseline on main"
    - "E4-T3 | done | public offer detail with masked source text (PRs #78/#79)"
    - "E6-T4 | done | identity sessions/rate limits (PR #51)"
branch:
  required: true
  name: feat/E6-T5-contact-masking-reveal
  task_id: E6-T5
  one_task_only: true
  created_at: null
  pull_request: null
completion:
  completed_by: null
  completed_at: null
  pull_request: null
  evidence: []
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E6-T5: Implement contact masking, encryption, reveal, and audit

## Outcome

Server-side contact encryption/masking and an authenticated audited reveal endpoint exist so anonymous clients never receive raw phones/handles, while active accounts can reveal contacts only for publicly visible offers.

## Scope

- Extracted phone/Telegram spans persist as `ContactPoint` rows: AES-GCM ciphertext, keyed HMAC fingerprint, safe `masked_value`, revealability flag.
- Public offer/detail/source projections continue to use server-built masked text only (already partially present via ingestion); prove anonymous responses contain no raw extracted contact.
- Authenticated `POST /api/v1/offers/{offer_id}/contacts/reveal` with origin/CSRF JSON guards, per-user rate limits, `Cache-Control: no-store, private`, and minimized `ContactReveal` audit (user/offer/request/outcome/timestamp; never contact, IP, or user-agent).
- Additive Alembic migration; OpenAPI + frontend codegen; unit/integration/security tests.
- Production dependency: `cryptography` (E0 spike selection).

## Out of scope

- Frontend reveal UX / English i18n keys (E6-T6).
- Owner administration console and reveal-audit UI (E6-T7).
- Production HTTPS activation of registration/reveal (E7-T7 after E7-T10/D-009).
- Formal privacy notice / retention policy.

## Affected modules and contracts

- New contacts feature slice under `apps/backend/src/wef_backend/features/`, ingestion persistence wiring, composition/settings secrets, migration head, `contracts/openapi/v1.json`, `apps/web/src/generated/api.ts`, [AUTH_ADMIN_CONTACTS](../../../security/AUTH_ADMIN_CONTACTS.md), [DATA_MODEL](../../../contracts/DATA_MODEL.md), [HTTP_API](../../../contracts/HTTP_API.md).

## Implementation notes

- Reuse E6-T4 session resolution, origin checks, and `MemoryRateLimiter`.
- Visibility gate matches offer detail (`OfferVisibility.VISIBLE`); IDOR and non-visible offers fail closed without leaking hidden contacts.
- Forced-password-change and inactive accounts cannot reveal.
- Fail closed when encryption keys are unset.
- Domain/application layers must not import fastapi/sqlalchemy/pydantic (import-linter).

## Acceptance criteria

- [ ] Anonymous map/detail/source responses contain no raw extracted phone/handle.
- [ ] Active users not awaiting forced password change can reveal only contacts for visible offers.
- [ ] Anonymous, disabled, forced-password-change, rate-limited, and IDOR attempts fail without leakage.
- [ ] Audit records user/offer/request/outcome/timestamp but never contact, IP/hash, or user-agent.
- [ ] Reveal responses carry `Cache-Control: no-store, private`.
- [ ] OpenAPI change is additive; frontend client regenerates; CI format/lint/type/test/contract gates pass.
- [ ] `EXPECTED_DATABASE_REVISION` matches the new migration head.

## Test plan

- Unit: mask helpers, AES-GCM round-trip, HMAC stability, authorization matrix.
- Integration: persist contacts on ingest/seed path; reveal happy path; negative authz/rate-limit/IDOR; audit column probes.
- Contract: deterministic OpenAPI export + codegen + oasdiff additive-only.
- Security: no plaintext/ciphertext/keys in public JSON or structured log events for reveal paths.

## Rollback

Redeploy previous image; additive tables remain unused. No backup claims (ADR-015).
