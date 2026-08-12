---
schema: ai-docs/adr@1
id: ADR-016
title: Username/password accounts and owner-only admin console
status: accepted
date: 2026-08-12
supersedes: [ADR-011]
superseded_by: []
resolves: [D-004, D-008]
---

# ADR-016: Username/password accounts and owner-only admin console

- Status: accepted
- Date: 2026-08-12
- Decision: allow public username/password registration without email collection, verification, or self-service recovery. A fixed `owner` role manages users, session revocation, forced password resets, and reveal audits through an ActiveAdmin-like server-rendered console based on Starlette Admin.
- Rationale: logged-in account IDs are sufficient for the requested contact-reveal audit, while transactional email and privacy-notice work are out of scope.
- Consequence: an account is pseudonymous and does not establish a real person's identity. Reveal audit stores user/offer/request/outcome/timestamp only, not contact value, IP hash, or user-agent. Owner actions use application interactors and are audited; generic admin CRUD never exposes password hashes, session tokens, encrypted contacts, or secrets.
- Security constraint: no owner username/password is hardcoded in source, image, migration, or committed environment. A one-time GitHub Actions secret bootstraps the first owner into PostgreSQL with an Argon2 hash, then the bootstrap credential is removed/rotated. Admin and user authentication remain disabled until HTTPS.
- Library decision: Starlette Admin is preferred for SQLAlchemy integration, custom authentication, per-view permissions, and custom actions. FastAPI Admin is rejected because it introduces TortoiseORM and Redis; SQLAdmin remains a fallback but requires explicit secure cookie and CSRF hardening.
- Supersedes: [ADR-011](ADR-011-accounts-gate-contact-reveal.md)'s email-verification/reset/email-delivery requirements, not its anonymous-browsing and separate audited reveal boundary.
- Resolves/reframes: [D-004](../deferred/D-004-authentication-curation.md) and [D-008](../deferred/D-008-transactional-email-provider.md).
