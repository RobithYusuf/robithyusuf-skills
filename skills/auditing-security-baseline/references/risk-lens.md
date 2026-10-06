# Cross-Stack Risk Lens

Prompts for noticing likely risk areas. Verify each against the actual codebase and skip surfaces that are not present.

## Entry points and trust boundaries
- Identify public, authenticated, admin, webhook, worker, CLI, and scheduled entry points.
- Verify each boundary has the expected authentication, authorization, validation, and logging.

## Client-visible data
- Treat frontend code, SSR/bootstrap payloads, page props, route manifests, API responses, source maps, and browser storage as public.
- Check that only UI-required fields are sent and that admin/internal data is not shipped to lower-privilege users.

## Identity and access
- Review login, MFA, password reset, token/session lifecycle, logout, re-authentication, and high-privilege access.
- Check object/resource ownership and role/permission enforcement on every sensitive request.

## State-changing and critical flows
- Pay extra attention to payments, billing, inventory, activation codes, credential changes, file upload, import/export, and admin actions.
- Look for missing transactions, locks, idempotency, replay protection, duplicate-processing guards, and audit logs.

## Environment and deployment
- Compare local/staging/prod config for security drift: debug mode, cookies, CORS, CSP/security headers, TLS/proxy trust, secrets, storage, DB, cache, queue.
- Check infrastructure assumptions: private networks, least-privilege credentials, backup/restore needs, and whether runtime config matches app code.

## External clients and integrations
- Treat secrets embedded in mobile apps, desktop apps, browser extensions, and frontend bundles as public.
- Check webhook signatures, CORS/allowed headers, device/client validation, rate limits, and revocation/rotation paths.

## Background work and storage
- Check worker/queue/cron retry safety, idempotency, payload sensitivity, overlap protection, and durability of critical queues.
- Check file/object storage visibility, path traversal, signed URL use, public buckets, and executable upload risks.

## Multi-tenant and admin surfaces
- Confirm tenant scoping in queries, jobs, cache keys, storage paths, and webhooks.
- Check that impersonation/support/admin flows are constrained, logged, and separated from public surfaces.
