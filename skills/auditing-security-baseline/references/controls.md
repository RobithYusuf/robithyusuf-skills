# Security Baseline Controls

Full control list by tier. Items marked **(SPA)** apply to projects with client-side rendering or hybrid SSR/SPA; skip them when nothing renders client-side.

## Contents

- 1. Core controls (every project)
- 2. Application safety (most projects)
- 3. Hardening (when the feature exists)
- 4. Operational security (maturity)
- Applicability notes

## 1. Core controls (every project)

### Authentication
- Protect all sensitive endpoints with authentication.
- Enforce token/session expiration and re-authentication for sensitive actions.
- Do not rely on client-side checks for access control.

### Authorization (access control)
- Enforce authorization on every request (role/permission/ownership).
- Prevent IDOR by checking resource access against the authenticated principal.
- Use least-privilege defaults; deny by default when unsure.
- (SPA) Apply data-level authorization: filter response fields by user role before sending to the client.
- (SPA) Do not expose admin/internal route maps or endpoint structures to unprivileged users.

### Password security (if accounts exist)
- Store passwords with bcrypt/argon2 using appropriate cost parameters.
- Never log or return passwords, password hashes, reset tokens, or secrets.
- Use one-time, short-lived password reset tokens.

### Input validation and output encoding
- Validate all inputs on the server (type, length, format, ranges).
- Use allow-lists for structured fields and strict parsing for JSON bodies.
- Encode output for its context (HTML, attribute, URL, JS) to reduce XSS risk.

### Injection prevention
- Use parameterized queries / safe ORM patterns for SQL.
- Avoid string concatenation for queries, shell commands, or interpreters.
- Constrain dynamic filters/sorts (allow-list column names); avoid raw query fragments.

### Transport security
- Enforce HTTPS only and secure redirects.
- Disable weak TLS configurations; prefer modern protocols and ciphers.

### Secrets management
- Keep secrets out of source control (no hardcoded keys, tokens, or credentials).
- Load secrets from the environment or a secret manager; restrict access by least privilege.
- Separate secrets per environment and rotate when exposure is suspected.

### Error handling (safe failures)
- Return generic errors to clients; never expose stack traces or internal details.
- Use structured server logs for diagnostics.
- Ensure failures do not leak sensitive data in responses.
- (SPA) Ensure server error details are not serialized into client-side page props or state.

### Logging (security-relevant events)
- Log authentication failures, authorization denials, and critical state changes.
- Include request correlation IDs and actor identifiers.
- Do not log sensitive payloads (tokens, passwords, PII) unless explicitly redacted.

### Data protection basics
- Minimize collected data; store only what is needed.
- Classify sensitive fields (PII, tokens, credentials) and handle them accordingly.
- (SPA) Treat all data sent to the client as public: page props, API responses, and embedded JSON are readable via view-source, DevTools, or curl.
- (SPA) Send only the fields the UI needs; never pass full database models/rows to the frontend.

## 2. Application safety (most projects)

### Session and token security
- Prefer short-lived access tokens; validate issuer/audience where applicable.
- Store tokens securely (HttpOnly cookies for web sessions; avoid localStorage for high-risk apps).
- Revoke/rotate refresh tokens and invalidate sessions on logout or credential changes.
- (SPA) Encrypt or clear browser history state on logout to prevent back-button data leaks.
- (SPA) Remove bootstrap data attributes (for example `data-page`, `__NEXT_DATA__`) from the DOM after hydration.

### Rate limiting and abuse controls
- Rate-limit login, password reset, and other sensitive endpoints.
- Add burst control and per-user limits for APIs.
- Use exponential backoff or temporary blocks for repeated failures.

### Race conditions and idempotency (state changes)
- Use transactions and locking where concurrent updates are possible.
- Make non-repeatable operations idempotent (idempotency keys for payments, bookings, etc.).
- Prevent double-submit and duplicate processing.

### File upload security (if supported)
- Enforce size limits and allow-lists for file types.
- Verify content type (do not trust extensions); store outside public paths.
- Scan uploads when risk warrants; never execute uploaded content.

### Database security
- Use least-privilege DB accounts; separate read/write roles where possible.
- Restrict network access to the database; enable encryption in transit.
- Encrypt and access-control backups.

### Backup and recovery
- Back up critical data regularly.
- Test restore procedures periodically.
- Define RPO/RTO targets appropriate to the product.

### Client-side data exposure (SPA / frontend-rendered apps)
- All data passed to the client (page props, initial state, API responses) is publicly visible.
- Select only the fields the UI requires; never pass full ORM models or unfiltered query results.
- Filter shared/global data (navigation, config, user context) to exclude internal details.
- Do not embed internal IDs, cost prices, profit margins, or business-logic constants in client payloads.
- If the framework exposes a route map to the client (for example Ziggy or file-based routing manifests), filter it by the current user's role so admin/internal routes are not disclosed.
- Periodically audit the page source of production pages: `data-page` attributes, `__NEXT_DATA__` scripts, embedded JSON, and initial store state.

## 3. Hardening (when the feature exists)

### CSRF protection (cookie-based auth)
- Use CSRF tokens and SameSite cookie settings.
- Require anti-CSRF protection on all state-changing requests.

### CORS (cross-origin access)
- Allow only the necessary origins, methods, and headers.
- Never combine wildcard origins with credentials.

### Security headers (web apps)
- Enable baseline headers: CSP, HSTS, `frame-ancestors` / `X-Frame-Options`.
- Tighten CSP over time to reduce XSS impact.
- Set `Referrer-Policy` to limit referrer leakage (for example `strict-origin-when-cross-origin`).
- Set `Permissions-Policy` to disable unused browser features (camera, geolocation, microphone).

### SSRF protection (URL fetch, webhooks, "import from URL")
- Block internal IP ranges and cloud metadata endpoints, including after redirects and DNS resolution.
- Use domain allow-lists where feasible and enforce timeouts.

### Encryption at rest (sensitive data)
- Encrypt secrets and high-risk PII fields at rest.
- Use proper key management and rotation policies.

### DoS resilience (basic)
- Enforce request size limits, timeouts, and concurrency limits.
- Protect expensive endpoints with caching and quotas where possible.

## 4. Operational security (maturity)

### Dependency and supply-chain security
- Pin dependencies where practical (lockfiles committed); update regularly.
- Scan dependencies for known vulnerabilities and remediate promptly.

### Security testing
- Add automated checks (SAST/DAST) where feasible.
- Periodically test access control and auth flows manually.
- (SPA) Include a view-source / page-props audit in security reviews of client-rendered pages.

### Admin and privileged access
- Require MFA for admin and high-privilege accounts.
- Separate admin interfaces from public surfaces and log admin actions.
- (SPA) Ensure admin-only data and route definitions are not included in responses to non-admin users.

### Audit trail (when required)
- Record who did what, and when, for sensitive operations.
- Protect audit logs from tampering and limit access to them.

### Incident response basics
- Maintain a process for secret rotation, token revocation, and user notification.
- Keep an inventory of critical assets and access paths.

### Privacy and retention
- Define data retention and deletion policies.
- Support deletion/export requirements imposed by regulation or contracts.

## Applicability notes

- Core controls apply to every project by default.
- Hardening controls are enabled when features or risk require them.
- Security is enforced on the server; clients are not trusted.
- Skip a control only when it is clearly not applicable. When in doubt, review the design and assume it applies.
