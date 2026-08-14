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
