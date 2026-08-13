---
schema: ai-docs/adr@1
id: ADR-010
title: Isolate WEF on the shared NUC
status: accepted
date: 2026-08-12
supersedes: []
superseded_by: [ADR-020]
resolves: []
---

# ADR-010: Isolate WEF on the shared NUC

- Status: accepted for MVP
- Date: 2026-08-12
- Decision: deploy as the distinct Compose project `wef-production` under `/home/nuc/wef`, with project-owned networks, persistent paths, service names, and no shared database/container with existing applications.
- Rationale: the target host already runs DuckDNS, WireGuard, and an AI Forecast stack. WEF must be independently deployable and removable.
- Consequence: do not use explicit generic `container_name` values, do not bind host ports 3000, 8080, or UDP 51820, and do not modify/restart existing Compose projects. WEF exposes configurable `WEF_PUBLIC_PORT`, initially 3100/TCP, after a deployment-time conflict check.
- Partial supersession: [ADR-020](ADR-020-use-nginx-shared-tls-ingress.md) preserves application/data isolation but permits a separately approved, inventoried, and rollback-tested shared Nginx TLS ingress for WEF and the existing AI Forecast service.
