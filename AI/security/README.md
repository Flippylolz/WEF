# Security

This domain owns identity, sessions, authorization, contact protection, reveal auditing, and owner administration behavior.

## Canonical documents

- [Authentication, administration, and contact reveal](AUTH_ADMIN_CONTACTS.md) — username registration, login/session behavior, password changes, owner resets, masking, reveal authorization, administration, and auditing.
- [Verified delivery automation evidence](../quality/DEPENDABOT_EVIDENCE_COVERAGE.md) — existing required-check and bot-identity enforcement for the scheduled Dependabot controller, traced to E1-T7 and ADR-023.
- [Operational validation evidence](../quality/OPERATIONS_COMPLETE_COVERAGE.md) — parsed HTTPS redirect authority checks reject hostname-prefix/userinfo lookalikes; complete operational Python coverage protects existing deployment and non-interference guards.
- [Deployment semantic health evidence](../quality/EMBEDDED_DEPLOYMENT_COVERAGE.md) — wrong public liveness/product bodies cannot fall through to success inside the deployment conditional; collector exports remain source-free.
- [Runtime shell evidence](../quality/RUNTIME_SHELL_COVERAGE.md) — failed application/worker starts refuse activation and reach rollback; certificate permissions, scoped renew/reconnect commands and complete source coverage use isolated synthetic fixtures.

## Confirmed security model

The backend lockfile uses pyasn1 0.6.5, the existing RSA/Telegram transitive
dependency's security patch. Its [upstream release](https://github.com/pyasn1/pyasn1/releases/tag/v0.6.5)
fixes four quadratic CPU-consumption advisories affecting 0.6.4. Retain the
dependency audit gate; do not suppress these findings to unblock unrelated work.

- Browsing is anonymous and read-only.
- Restricted actions use pseudonymous username/password accounts; no email verification or self-service email recovery is required.
- The fixed `owner` role alone administers users, session revocation, forced password resets, and reveal audits through the server-rendered owner console.
- Public responses mask contacts. A separate authenticated endpoint performs authorized, rate-limited, audited reveal.
- Passwords, hashes, session tokens, decrypted contacts, secrets, and owner bootstrap credentials never appear in source, images, logs, public responses, or generic admin forms.
- User/admin authentication and contact reveal are enabled on the verified HTTPS origin after E7-T7; plain `:3100` remains a Secure-cookie-incompatible rollback path.
- The web app layers a per-request nonce `Content-Security-Policy` (no `script-src 'unsafe-inline'`) over the static shared-edge policy in `infra/nginx/tls.conf.in`; browsers enforce all delivered policies, so first-party scripts require the app-issued nonce while the edge directive set stays unchanged.

Security-affecting changes require an accepted decision, threat-appropriate tests, redacted audit behavior, and explicit traceability to product and contract requirements.
