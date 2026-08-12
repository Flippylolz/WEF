# Security

This domain owns identity, sessions, authorization, contact protection, reveal auditing, and owner administration behavior.

## Canonical documents

- [Authentication, administration, and contact reveal](AUTH_ADMIN_CONTACTS.md) — username registration, login/session behavior, password changes, owner resets, masking, reveal authorization, administration, and auditing.

## Confirmed security model

- Browsing is anonymous and read-only.
- Restricted actions use pseudonymous username/password accounts; no email verification or self-service email recovery is required.
- The fixed `owner` role alone administers users, session revocation, forced password resets, and reveal audits through the server-rendered owner console.
- Public responses mask contacts. A separate authenticated endpoint performs authorized, rate-limited, audited reveal.
- Passwords, hashes, session tokens, decrypted contacts, secrets, and owner bootstrap credentials never appear in source, images, logs, public responses, or generic admin forms.
- User/admin authentication and contact reveal remain disabled until HTTPS and required secrets are in place.

Security-affecting changes require an accepted decision, threat-appropriate tests, redacted audit behavior, and explicit traceability to product and contract requirements.
