---
schema: ai-docs/deferred-decision@1
id: D-009
title: Shared TLS hostnames and forwarding
status: deferred
task_gates:
  - E7-T10
resolved_by: []
---

# D-009: Shared TLS hostnames and forwarding

- Status: deferred until E7-T10 live rollout; approved E7 spike revision 3 permits only inert topology and cutover-automation work before resolution.
- Context: [ADR-020](../adr/ADR-020-use-nginx-shared-tls-ingress.md) selects Nginx/Certbot and requires independently routable HTTPS origins for WEF and the existing AI Forecast service currently exposed on port 3000.
- Required owner inputs:
  - Approve two stable public hostnames; one hostname cannot independently route two root applications without verified path-prefix support.
  - Confirm both DNS records resolve to the NUC's current public address.
  - Confirm router/firewall forwarding sends public TCP 80/443 to the NUC during the controlled migration.
- Recommended resolution: retain the existing DuckDNS name for AI Forecast and register a second free DuckDNS hostname for WEF, then route both through Nginx on standard 443.
- Alternative: approve and prove path-prefix compatibility for both applications on one hostname. Do not assume this works for Next.js assets, API paths, cookies, redirects, or the existing AI Forecast application.
- Rejected default: long-term public HTTPS on application ports 3000/3100. Certificates are hostname-bound rather than port-bound, and public application ports complicate redirects, monitoring, firewall policy, and future service migration.
- Evidence required to resolve: owner-approved names, DNS lookups, external 80/443 reachability while Nginx is listening, successful ACME staging issuance, and independent host-header routing tests.
- Progress while deferred: E7-T8 may prove the isolated topology and E7-T9 may prove reversible automation with reserved fixture names and local listeners. Neither may register names, issue public certificates, alter forwarding, or activate the server.
- Progress as of 2026-08-20:
  - E7-T8 `done` (PR #69): inert Nginx topology + Pebble ACME fixtures.
  - E7-T9 `done` (PRs #106–#108): reversible cutover/preflight/smoke/rollback automation; no live NUC mutation.
  - NUC check: WEF on `:3100`, Forecast on `:3000`, no host listeners on 80/443; public `:80` remap to WEF (if present) is not Nginx ACME readiness.
  - Proposed E7 plan revision 6 sequences only E7-T10 after this decision resolves; see [PROPOSED_IMPLEMENTATION_PLAN-revision-6](../../epics/E7-production-delivery/PROPOSED_IMPLEMENTATION_PLAN-revision-6.md) and operations [B-009](../../operations/BLOCKERS.md).
- Owner checklist to resolve:
  - [ ] Two hostnames approved (or path-prefix alternative proven).
  - [ ] DNS A/AAAA for both names → NUC public IP verified from outside the LAN.
  - [ ] Router/firewall forwards public TCP 80 and 443 to the NUC (Nginx will bind them during cutover).
  - [ ] Record the approved names and verification evidence in this file's `resolved_by` / resolution notes; set `status: resolved`.
