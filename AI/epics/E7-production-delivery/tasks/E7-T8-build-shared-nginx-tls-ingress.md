---
schema: ai-workflow/task@1
id: E7-T8
epic: E7
title: "Build isolated shared Nginx TLS topology"
status: ready
revision: 2
priority: P1
size: M
milestone: M3
dependencies: [E7-T4]
requirement_ids: []
decision_ids: [ADR-010, ADR-014, ADR-019, ADR-020]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E7-T8-build-shared-nginx-tls-ingress.md
  promoted_by: "Cursor Agent (owner-authorized)"
  promoted_at: "2026-08-13T19:32:59Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T19:32:59Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T19:32:59Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T19:32:59Z"
  evidence:
    - "E7-T4 | done | merged PR https://github.com/Flippylolz/WEF/pull/19 | integrated on main"
branch:
  required: true
  name: null
  task_id: E7-T8
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

# E7-T8: Build isolated shared Nginx TLS topology

> Revision 2 narrows the former live-cutover candidate to inert, locally provable shared-edge infrastructure. D-009 remains a gate for E7-T10 and is not required for this task.

## Outcome

Provide a separately managed Nginx/Certbot edge topology whose two-host routing, HTTP-01 bootstrap, certificate renewal, validation, graceful reload, persistence, and failure behavior are proven without changing the production server.

## Scope

- Add a dedicated shared-edge Compose project and filesystem boundary independent from ordinary WEF releases.
- Add an HTTP-only ACME bootstrap configuration and generated two-host TLS configuration using fixture hostnames in CI.
- Persist the complete Certbot state and ACME webroot; mount generated Nginx configuration and certificates read-only.
- Run Nginx least-privileged with bounded logs, health checks, a read-only root filesystem, and only reviewed writable/capability exceptions.
- Render non-interactive Certbot webroot issuance/renewal and a success-only deploy hook that runs `nginx -t` before graceful reload.
- Add local upstream fixtures and deterministic positive/negative topology/configuration proofs.

## Out of scope

- Production DNS, public ACME issuance, router/firewall changes, ports 80/443 on the NUC, or any remote server mutation.
- WEF Caddy removal, AI Forecast changes, application listener changes, redirect activation, or live certificate/expiry evidence.
- Registration, sessions, administration, contact reveal, historical import, backups, and DNS-01 credentials/plugins.

## Affected modules and contracts

- `infra/compose.shared-edge.yaml` and `infra/nginx/` own the inert edge model and templates.
- `scripts/deploy/` owns deterministic rendering, validation, renewal-hook, and local proof commands.
- `scripts/prove_shared_edge_topology.py` owns repository-level positive/negative policy checks.
- No public API, persisted application schema, application image, or production data contract changes.

## Implementation notes

- Use reserved `.test` hostnames and synthetic fixture certificates only.
- Nginx bootstrap and TLS configurations must validate independently so missing production certificates cannot prevent HTTP-01 startup.
- Certbot state is one persistent tree; do not copy individual `live/` files or break Certbot-managed symlinks.
- `certbot renew --dry-run` skips deploy hooks by default; the proof explicitly requests the hook and verifies that failed validation prevents reload.
- The external edge network is created/owned by the edge boundary and must not be removed by WEF cleanup.

## Acceptance criteria

- [ ] Shared-edge Compose renders deterministically with pinned images, a dedicated project/network, persistent Certbot state, bounded logs, health checks, and least privilege.
- [ ] HTTP-only bootstrap serves only ACME challenge traffic and does not redirect before both TLS routes are available.
- [ ] Generated fixture configuration has distinct WEF and AI Forecast virtual hosts, correct proxy headers/timeouts/body limits, conservative security headers, and no committed production hostname.
- [ ] `nginx -t` passes for valid bootstrap/TLS fixtures and rejects missing certificates, duplicate names, unsafe paths, and invalid configuration before reload.
- [ ] Renewal uses saved webroot settings, persistent state, unattended execution, a passing dry run, and a success-only validated graceful reload hook.
- [ ] Secrets, private keys, ACME account data, generated production environments, and unreviewed host output are excluded from Git, logs, artifacts, and image layers.
- [ ] Local failure tests prove invalid config, failed renewal, failed reload validation, and unavailable fixture upstreams do not replace the last valid configuration.
- [ ] No production/server/network mutation occurs.

## Test plan

- Unit/static: renderer input validation, reserved fixture names, path ownership, image pins, ports, capabilities, mounts, log limits, and secret patterns.
- Integration: Compose render, Nginx bootstrap/TLS validation, two fixture host routes, proxy headers, ACME challenge, health checks, and graceful reload.
- Certificate lifecycle: synthetic issuance layout, renewal command/dry run, deploy-hook success/failure, and unchanged active config after failure.
- Repository: format, lint, type, tests, Markdown links, shell syntax/shellcheck, production proof, and runtime image checks.

## Rollout and rollback

This task is inert. Roll back by reverting its dedicated PR; it creates no production listener, certificate, state, network, or application change.

## Ready checklist

- [x] This file is authoritative under `tasks/`; its proposed source is removed.
- [x] Promotion and approved spike revision 3 are recorded.
- [x] Approved implementation-plan revision 3 and completed E7-T4 dependency evidence are recorded.
- [x] D-009 is absent because live rollout belongs to E7-T10.

## Start checklist

- [ ] Status passed through `ready`.
- [ ] Dedicated E7-T8 branch is created and recorded.
- [ ] Branch contains E7-T8 only.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
