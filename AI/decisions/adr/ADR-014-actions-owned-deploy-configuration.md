---
schema: ai-docs/adr@1
id: ADR-014
title: GitHub Actions owns deploy-time configuration
status: accepted
date: 2026-08-12
supersedes: []
superseded_by: []
resolves: []
---

# ADR-014: GitHub Actions owns deploy-time configuration

- Status: accepted
- Date: 2026-08-12
- Decision: non-secret production values live in GitHub Actions variables and sensitive values in GitHub Actions secrets. Every deployment reconstructs the complete release configuration under `/home/nuc/wef/secrets/releases/<git-sha>/` and atomically updates `/home/nuc/wef/secrets/current`; no production `.env` is committed.
- Rationale: GitHub is the requested deployment source of truth and each release must receive known configuration without manual server drift.
- Consequence: workflows never print secret values, use mode-0600 temporary/target files, validate before atomic activation, retain only the current/rollback-safe configuration needed on the host, and delete transfer temporaries on success/failure. Local development uses `.env.example` plus ignored local values.
