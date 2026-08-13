---
schema: ai-docs/adr@1
id: ADR-019
title: Separate the anonymous HTTP rehearsal from public launch
status: accepted
date: 2026-08-12
supersedes: []
superseded_by: []
resolves: [D-001]
---

# ADR-019: Separate the anonymous HTTP rehearsal from public launch

- Status: accepted
- Date: 2026-08-12
- Decision: deploy the synthetic, anonymous, read-only map MVP to the supplied NUC first through plain HTTP on configurable port `3100`. Treat this as a production-infrastructure rehearsal, not public-launch completion. Registration, sessions, owner administration, contact reveal, historical data, and Telegram stay disabled until their own approved tasks, the E7-T8 shared Nginx HTTPS gate, and the E7-T7 sensitive-feature gate pass.
- Rationale: the host, DuckDNS name, router port, Docker access, persistence path, and anonymous MVP are available now. Coupling an infrastructure rehearsal to unfinished authentication/contact/privacy work would delay verification without making those sensitive features safer.
- Consequences:
  - E7-T1 through E7-T4 may deliver isolated Compose, provisioning, immutable release automation, health checks, and compatible application rollback for anonymous synthetic data.
  - E6 security/diagnostic tasks remain required for the features and public-launch scope they govern, but no longer block the bounded anonymous rehearsal topology.
  - `http://2fa54e2405.duckdns.org:3100` is interim only. No password, session cookie, contact detail, private source record, or Telegram credential may cross it.
  - E7-T8 requires approved shared Nginx/Certbot HTTPS routing before E7-T7 may combine it with the E6 registration/contact/admin dependencies and enable sensitive functionality.
- Safety constraints:
  - The server boundary remains `/home/nuc/wef`, Compose project `wef-production`, and the single configured edge port.
  - The first release contains only clearly marked synthetic fixture data.
  - GitHub Actions startup blocker B-006 prevents claiming automated delivery operational until a hosted release run succeeds.
  - No global Docker cleanup, existing-project mutation, privileged host change, or stored sudo credential is allowed.
- Reversal: stop the WEF Compose project and remove only `/home/nuc/wef` after explicit owner authorization, or replace interim HTTP with the reviewed E7-T8 Nginx HTTPS configuration.
