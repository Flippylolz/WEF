# October 2026 runtime and tooling refresh

This is unplanned owner-requested maintenance following the Dependabot repairs.
Stable package registries and upstream image registries were checked on
2026-10-19. The selected versions are Python 3.13.16, Node.js 22.23.3, uv 0.13.1,
pnpm 12.14.0, oasdiff 1.34.0, the current Dockerfile frontend, Caddy 2.11.7, stable Nginx 1.30.6, and Certbot 5.8.0. Runtime images
remain pinned to immutable multi-platform digests. PostGIS uses the current
patched digest of the existing PostgreSQL 17 / PostGIS 3.5 image line.

Language and database version families remain unchanged. Python 3.14/3.15,
Node.js 24/26, PostgreSQL 18, and PostGIS 3.6 would require their own compatibility
and database-extension migration review. TypeScript's native compiler is already
7.0.2; its JavaScript API companion remains the latest TypeScript 6 compatibility
package, as required by the existing Next/ESLint/OpenAPI integration.

The pnpm 12 launcher is native. Its package-manager metadata is committed in the
lockfile, with the application dependency graph preserved. Docker, CI, package
manifests, local tool versions, and setup documentation use the same selected
versions. The existing immutable Nginx/Certbot topology proofs follow the new
image pins; no deployment topology or configuration ownership changes.

Validation includes locked install, format/lint/type/test/contract gates, runtime
image builds, Compose checks, and the deployment/shared-edge runtime proofs.
No application or database migration is introduced. Roll back by reverting this
PR's squash commit to restore the previous tools and image digests.
