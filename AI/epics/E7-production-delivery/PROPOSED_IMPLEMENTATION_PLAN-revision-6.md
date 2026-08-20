---
schema: ai-workflow/implementation-plan@1
epic: E7
title: "Live shared TLS rollout after D-009"
status: awaiting_approval
revision: 6
owner: owner
spike_revision: 4
task_sequence:
  - id: E7-T10
    revision: 1
approval:
  required_role: owner
  status: pending
  decided_by: null
  decided_at: null
  approved_revision: null
  evidence: null
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Proposed Implementation Plan revision 6: Live shared TLS rollout

> **Awaiting approval.** Do not promote or start E7-T10 until D-009 is resolved and this revision is owner-approved.

## Why now

- [E7-T8](tasks/E7-T8-build-shared-nginx-tls-ingress.md) and [E7-T9](tasks/E7-T9-implement-reversible-shared-edge-cutover.md) are `done` (PRs #69, #106–#108). Inert topology and reversible cutover automation exist with fixture proofs only.
- Live NUC mutation, real DNS/ACME, and public 80/443 cutover remain blocked on [D-009](../../decisions/deferred/D-009-shared-tls-hostnames-and-forwarding.md).
- [E7-T7](proposed-tasks/E7-T7-enable-production-registration-and-contact-reveal.md) and [E7-T11](proposed-tasks/E7-T11-activate-the-verified-historical-candidate.md) stay proposed behind E7-T10 plus their other gates.

## Approved spike baseline

- [Spike revision 4](SPIKE.md) remains current.
- Binding constraints for this plan: owner-resolved hostnames, DNS to the NUC, router/firewall forwarding of public TCP 80/443 to the NUC, staging ACME proof, then production cutover with automatic rollback on smoke failure.

## Scope and outcome

Execute the live shared-edge migration on the NUC so WEF and AI Forecast terminate TLS on Nginx at standard 443 with independent hostnames (recommended) or an owner-proven path-prefix design. Preserve Caddy `:3100` and Forecast `:3000` as rollback material until cutover is verified.

## Ordered task sequence

### 1. E7-T10 — Roll out and verify shared TLS

- Task: [E7-T10](proposed-tasks/E7-T10-roll-out-and-verify-shared-tls.md) (promote only after this plan is approved and D-009 is resolved).
- Independently reviewable: live inventory/preflight, staging then production ACME, staged cutover (`tls → https-smoke → redirect → redirect-smoke`), dual-origin verification, and documented rollback to the previous validated listeners.
- Dependencies: E7-T9 `done`; deferred gate D-009 resolved with evidence recorded in the decision file.
- Affected modules/contracts: no public API contract change; production Compose/edge release activation on the NUC; operations docs and blocker log updates.
- Tests/verification: external HTTPS reachability for both origins, ACME renewal dry-run, host-header routing, smoke suite from E7-T9 against live upstreams, rollback rehearsal evidence.
- Rollout: controlled server mutation only after owner hostname/DNS/forwarding confirmation; never invent or register DuckDNS names autonomously.

## Cross-task architecture

- Reuse E7-T8/E7-T9 scripts and overlays; do not re-implement cutover stages.
- Keep WEF and AI Forecast ownership boundaries: Forecast remains a host-listener upstream; WEF Compose never deletes the external edge network.
- Sensitive WEF features (registration, sessions, contact reveal) stay disabled until E7-T7 after this HTTPS gate.

## Security and operations

- Certificates and DuckDNS tokens stay off Git and off chat.
- No historical-candidate public activation (E7-T11) and no backup claims (ADR-015).
- Update [BLOCKERS](../../operations/BLOCKERS.md) B-002/B-009 when the live gate clears.

## Risks and mitigations

- **Single-hostname path-prefix:** rejected unless owner proves both apps; prefer two DuckDNS names.
- **Partial router forwarding:** external 80 mapped only to `:3100` is not ACME-ready; Nginx must own 80/443 on the NUC during cutover.
- **Forecast regression:** independent HTTPS smoke before redirects; auto-rollback on either origin failure.

## Invalidation triggers

Return to the spike for a different TLS terminator, shared-database edge ownership, or removal of dual-origin independence. Return to this plan if cutover stages or rollback boundaries change materially.

## Owner decision required

1. Resolve **D-009** (hostnames, DNS, 80/443 forwarding) with recorded evidence.
2. Approve **E7 IMPLEMENTATION_PLAN revision 6** (this document) or an updated successor.
3. Promote **E7-T10** and authorize live NUC cutover on a dedicated branch/PR sequence.

Until (1) and (2), autonomous agents continue other unblocked epic work and must not live-mutate shared TLS on the NUC.
