---
schema: ai-workflow/task@1
id: E7-T8
epic: E7
title: "Build isolated shared Nginx TLS topology"
status: done
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
  revalidated_by: "Owner (Flippylolz), 2026-08-16T06:04:21Z: the 2026-08-15 invalidation was an accidental touch by another agent's E7-T6 priority work"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T19:32:59Z"
  revalidated_by: "Owner (Flippylolz), 2026-08-16T06:04:21Z: the 2026-08-15 invalidation was an accidental touch by another agent's E7-T6 priority work"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T19:32:59Z"
  evidence:
    - "E7-T4 | done | merged PR https://github.com/Flippylolz/WEF/pull/19 | integrated on main"
branch:
  required: true
  name: feature/E7-T8-shared-edge-nginx
  task_id: E7-T8
  one_task_only: true
  created_at: "2026-08-15T15:19:18Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/69"
completion:
  completed_by: "ZCode agent (owner-directed)"
  completed_at: "2026-08-16T06:04:21Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/69"
  evidence:
    - "make shared-edge-proof | passed 2026-08-16 | scripts.prove_shared_edge_topology (compose policy, determinism, boundary ownership, secret exclusion, renderer negatives) and scripts.prove_shared_edge_runtime (nginx -t positive/negative, two-host TLS routing, proxy headers, hidden paths, security headers, body-limit enforcement, activation/rollback, renewal dry run with explicit deploy hook, failed-renewal and failed-validation no-reload proofs)"
    - "CI on PR #69 | all jobs green on head 39af375 2026-08-16, including Repository safety which runs make production-proof with both shared-edge proofs on Linux"
    - "python3 -m unittest scripts.test_shared_edge_render scripts.test_shared_edge_release | 20 tests OK"
    - "make format-check lint typecheck test contract-check compose-config production-proof | all passed locally"
    - "Linux-only correctness fixes proven in CI: deploy hooks are world-executable (capped root validates via the other permission class) and certbot keeps only the reviewed CHOWN/DAC_OVERRIDE/FOWNER tree-administration capabilities"
    - "Empirical note for E7-T9/E7-T10: certbot renew --dry-run forces the Let's Encrypt staging server unless --server is passed explicitly; the renewal orchestrator passes --deploy-hook explicitly alongside --run-deploy-hooks in dry runs"
    - "No production mutation: proofs use reserved .test hostnames, a local Pebble ACME server, temporary edge roots, and high local ports; the deploy workflow and compose.production.yaml are untouched"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E7-T8: Build isolated shared Nginx TLS topology

> Audit note: on 2026-08-15 another agent's E7-T6 prioritization work (PR #68) accidentally recorded this task as paused/invalidated while its dedicated-branch implementation was already in progress under owner instruction. The owner clarified on 2026-08-16 that the invalidation was unintended, restored the spike/implementation gates, and directed completion. The complete implementation and evidence live on PR #69.

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

- [x] Shared-edge Compose renders deterministically with pinned images, a dedicated project/network, persistent Certbot state, bounded logs, health checks, and least privilege.
- [x] HTTP-only bootstrap serves only ACME challenge traffic and does not redirect before both TLS routes are available.
- [x] Generated fixture configuration has distinct WEF and AI Forecast virtual hosts, correct proxy headers/timeouts/body limits, conservative security headers, and no committed production hostname.
- [x] `nginx -t` passes for valid bootstrap/TLS fixtures and rejects missing certificates, duplicate names, unsafe paths, and invalid configuration before reload.
- [x] Renewal uses saved webroot settings, persistent state, unattended execution, a passing dry run, and a success-only validated graceful reload hook.
- [x] Secrets, private keys, ACME account data, generated production environments, and unreviewed host output are excluded from Git, logs, artifacts, and image layers.
- [x] Local failure tests prove invalid config, failed renewal, failed reload validation, and unavailable fixture upstreams do not replace the last valid configuration.
- [x] No production/server/network mutation occurs.

## Test plan

- Unit/static: renderer input validation, reserved fixture names, path ownership, image pins, ports, capabilities, mounts, log limits, and secret patterns.
- Integration: Compose render, Nginx bootstrap/TLS validation, two fixture host routes, proxy headers, ACME challenge, health checks, and graceful reload.
- Certificate lifecycle: synthetic issuance layout, renewal command/dry run, deploy-hook success/failure, and unchanged active config after failure.
- Repository: format, lint, type, tests, Markdown links, shell syntax/shellcheck, production proof, and runtime image checks.

## Rollout and rollback

This task is inert. Roll back by reverting its dedicated PR; it creates no production listener, certificate, state, network, or application change.

## Completion evidence

- `make shared-edge-proof` passed 2026-08-16: `scripts.prove_shared_edge_topology` (compose policy, determinism, boundary ownership, secret exclusion, renderer negatives) and `scripts.prove_shared_edge_runtime` (nginx -t positive/negative, two-host TLS routing, proxy headers, hidden paths, security headers, body-limit enforcement, activation/rollback, renewal dry run with explicit deploy hook, failed-renewal and failed-validation no-reload proofs).
- `python3 -m unittest scripts.test_shared_edge_render scripts.test_shared_edge_release`: 20 tests OK.
- `make format-check lint typecheck test contract-check compose-config production-proof`: all passed.
- Empirical note for E7-T9/E7-T10: `certbot renew --dry-run` forces the Let's Encrypt staging server unless `--server` is passed explicitly; the renewal orchestrator therefore passes `--deploy-hook` explicitly alongside `--run-deploy-hooks` in dry runs.
- No production mutation: proofs use reserved `.test` hostnames, a local Pebble ACME server, temporary edge roots, and high local ports; the deploy workflow and `compose.production.yaml` are untouched.

## Ready checklist

- [x] This file is authoritative under `tasks/`; its proposed source is removed.
- [x] Promotion and approved spike revision 3 are recorded.
- [x] Approved implementation-plan revision 3 and completed E7-T4 dependency evidence are recorded.
- [x] D-009 is absent because live rollout belongs to E7-T10.

## Start checklist

- [x] Status passed through `ready`.
- [x] Dedicated E7-T8 branch is created and recorded.
- [x] Branch contains E7-T8 only.

## Done checklist

- [x] Acceptance criteria pass.
- [x] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [x] Completion actor, time, pull request, and evidence are recorded.
