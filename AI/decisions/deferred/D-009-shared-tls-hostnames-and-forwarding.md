---
schema: ai-docs/deferred-decision@1
id: D-009
title: Shared TLS hostnames and forwarding
status: resolved
task_gates:
  - E7-T10
resolved_by:
  - "Owner chat 2026-08-20: WEF hostname 2fa54e2405.duckdns.org; Forecast remains public :3000 only (no second shared-edge hostname)"
  - "Funbox port-forward screenshot 2026-08-20: public TCP 80→asusnuc:80 and 443→asusnuc:443; retain 3000/3100 for Forecast/WEF rollback"
  - "External probes 2026-08-20: DNS A 2fa54e2405.duckdns.org → 79.184.170.100; :3100 WEF and :3000 Forecast healthy; public :80/:443 time out until Nginx binds (Funbox cert no longer presented)"
---

# D-009: Shared TLS hostnames and forwarding

- Status: **resolved** (2026-08-20) for hostname assignment and router forwarding intent. ACME staging/production issuance and Nginx listener proof remain E7-T10 execution evidence.
- Context: [ADR-020](../adr/ADR-020-use-nginx-shared-tls-ingress.md) selects Nginx/Certbot. Owner amendment: initial shared-edge TLS covers **WEF only**; AI Forecast stays on host port **3000** and is not given a second public hostname in this cutover.
- Owner-approved resolution:
  - **WEF hostname:** `2fa54e2405.duckdns.org` (TLS on standard 80/443 via shared Nginx after E7-T10).
  - **AI Forecast:** no shared-edge hostname; remain reachable at `http://2fa54e2405.duckdns.org:3000` (and direct NUC :3000) until a later owner-approved Forecast TLS task.
  - **DNS:** `2fa54e2405.duckdns.org` → `79.184.170.100` verified externally.
  - **Forwarding:** Funbox rules forward public TCP **80→asusnuc:80** and **443→asusnuc:443**; keep **3000** and **3100** published for Forecast and interim WEF/Caddy rollback.
- Rejected for this cutover: second DuckDNS name for Forecast; path-prefix multiplexing of both apps on one hostname.
- Still rejected long-term for WEF: public HTTPS solely on application port 3100 (certificates are hostname-bound; WEF moves to 443).
- Evidence recorded above; E7-T10 must still prove ACME HTTP-01, certificate chain for `2fa54e2405.duckdns.org`, WEF smokes through Nginx, and Forecast `:3000` unchanged.
- Follow-on plan: [PROPOSED_IMPLEMENTATION_PLAN-revision-7](../../epics/E7-production-delivery/PROPOSED_IMPLEMENTATION_PLAN-revision-7.md) (WEF-only TLS).

## Owner checklist

- [x] Hostname assignment approved (WEF-only shared TLS; Forecast stays on :3000).
- [x] DNS A for WEF name → NUC public IP verified from outside the LAN.
- [x] Router/firewall forwards public TCP 80 and 443 to the NUC (screenshot + post-change timeout probes).
- [x] Decision recorded here with `status: resolved`.
