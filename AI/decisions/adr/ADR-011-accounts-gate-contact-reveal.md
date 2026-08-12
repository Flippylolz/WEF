---
schema: ai-docs/adr@1
id: ADR-011
title: In-house accounts gate contact reveal
status: accepted
date: 2026-08-12
supersedes: []
superseded_by: [ADR-016]
resolves: []
---

# ADR-011: In-house accounts gate contact reveal

- Status: anonymous/reveal boundary accepted; email-based identity details superseded by [ADR-016](ADR-016-pseudonymous-accounts-owner-console.md)
- Date: 2026-08-12
- Original decision: keep all property browsing anonymous, mask phone/Telegram contacts in public responses, and require an authenticated account for a separate audited reveal endpoint. [ADR-016](ADR-016-pseudonymous-accounts-owner-console.md) later replaced email verification with pseudonymous username/password accounts.
- Rationale: exposing contacts in public source text defeats tracking and enables scraping; requiring accounts for the whole map would add unnecessary friction.
- Current consequence: username registration, database-backed HttpOnly sessions, contact encryption/masking, reveal auditing, rate limits, HTTPS, and owner-administered password resets as defined by [ADR-016](ADR-016-pseudonymous-accounts-owner-console.md).
