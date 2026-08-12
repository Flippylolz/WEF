---
schema: ai-docs/deferred-decision@1
id: D-001
title: Production server and domain
status: deferred
task_gates:
  - E7-T2
resolved_by: []
---

# D-001: Production server and domain

- Status: partially resolved; complete before task E7-T2.
- Supplied access: `nuc@2fa54e2405.duckdns.org`.
- Observed 2026-08-12: Ubuntu 24.04.4/kernel 6.8, Intel Core 3 100U with 8 logical CPUs, approximately 7.3 GiB RAM with 6.3 GiB available, 936 GB root filesystem with 877 GB available, Docker 29.5.1, and Compose 5.1.3.
- Existing workloads: `duckdns-ddns`, `wireguard`, and `ai-forecast-production`; host ports 3000/TCP, 8080/TCP, and 51820/UDP are already allocated.
- Access constraint: `nuc` has Docker access but no passwordless sudo. Deployment uses `/home/nuc/wef` so automation never needs an administrative credential; request one from the owner only for an unavoidable privileged operation.
- Confirmed port: `WEF_PUBLIC_PORT=3100` initially, kept configurable.
- Router rule: owner reports 3100/TCP forwarding is configured. An external connection still times out while no WEF listener exists, so verify again after Caddy binds the port.
- Remaining input: implement public-launch HTTPS and set resource ceilings.
