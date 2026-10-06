---
name: auditing-security-baseline
description: Audits a codebase, branch, pull request, or deployment against a stack-agnostic security baseline (authentication, authorization and IDOR, session and token handling, input validation and injection, secrets, CORS and CSRF, security headers, client-side data exposure in SPA and SSR apps, file upload, SSRF, race conditions and idempotency, rate limiting, logging, and operational controls) and reports evidence-backed findings with severity, status, and fix direction. Use when reviewing a repo, feature, or PR for security issues, checking staging or production readiness, or drafting a hardening plan for a web app, API, mobile backend, worker, CLI, or SaaS, even if the user does not name this skill. Fits requests like audit keamanan, cek keamanan aplikasi, review keamanan PR, siap production, cek celah IDOR, data bocor di page props, hardening checklist, security review, security audit, is this safe to ship.
license: MIT
metadata:
  author: robithyusuf
  version: "1.1.0"
---

# Auditing Against a Security Baseline

A reusable, stack-agnostic baseline and audit workflow for any software project: web app, API, mobile backend, CLI, worker/service, SaaS, internal tool, or integration platform. The goal is a report of **evidence-backed** findings, not a generic checklist dump.

## Operating rules

- **Read-only by default.** Only change code when the user explicitly asks for fixes.
- **Never print raw secrets.** Report the file, key name, and exposure class (committed, shipped to client, logged), never the value.
- **No evidence, no finding.** Every claim cites a file:line, route, config key, command output, or reproducible behavior.
- **Separate certainty levels**: confirmed bugs vs. risks vs. items that need runtime validation.
- **Clients are public.** All client-side code and browser-visible data is readable by anyone; hidden UI or client checks are never authorization. Enforcement belongs on the server.
- **Pin the target.** In multi-environment audits, confirm which branch/environment is actually active before reporting.
- **Safe runtime checks only.** No destructive tests, production writes, or broad scans unless explicitly approved.

## Workflow

Copy this checklist and tick it off as you go:

```
- [ ] 1. Identify stack and trust boundaries
- [ ] 2. Inventory sensitive assets
- [ ] 3. Trace entry points (unauthenticated and authenticated)
- [ ] 4. Review authentication and authorization
- [ ] 5. Review client data exposure
- [ ] 6. Review state-changing and critical flows
- [ ] 7. Review deployment and environment controls
- [ ] 8. Run lightweight validators
- [ ] 9. Report using the output contract
```

**1. Stack and trust boundaries.** Map frontend, backend, API, workers, queues, database, storage, external providers, webhooks, admin panels, and extension/mobile clients. Infer the real architecture from code before applying any checklist (see "Framework adaptation" below).

**2. Sensitive assets.** Accounts, sessions, tokens, API keys, payment state, credentials, PII, files, audit logs, admin operations.

**3. Entry points.** Routes/controllers/handlers, API endpoints, RPC methods, jobs, webhooks, CLI commands, cron/scheduler tasks. Each boundary needs the expected authentication, authorization, validation, and logging.

**4. Auth and authorization.** Login flow, MFA for high-privilege access, middleware/guards/policies, ownership checks (IDOR), role boundaries, token/session invalidation on logout or credential change.

**5. Client data exposure.** Page props, SSR/bootstrap payloads, JSON APIs, route manifests, config shipped to clients, source maps, browser storage, logs/telemetry. Check that only UI-required fields are sent and that admin/internal data never reaches lower-privilege users.

**6. Critical flows.** Payments, subscriptions, booking/inventory, activation codes, password/email change, admin actions, file upload, import/export. Look for missing transactions, locks, idempotency, replay protection, duplicate-processing guards, and audit logs.

**7. Deployment and environment.** TLS/proxy trust, cookies, CORS, CSP/security headers, debug mode, secrets, storage visibility, cache/session/queue backends, DB privileges. Compare local/staging/prod for security drift.

**8. Validators.** Prefer cheap, focused checks; avoid heavy builds unless requested. Examples to adapt to the stack:

```bash
# dependency audit (pick what the project uses)
npm audit --omit=dev    # or pnpm audit / yarn npm audit
pip-audit               # Python
composer audit          # PHP
govulncheck ./...       # Go

# response headers and cookies on a deployed URL
curl -sI https://example.com/ | grep -iE 'strict-transport|content-security|x-frame|referrer-policy|permissions-policy|set-cookie|access-control'

# what the client actually receives (SSR/SPA bootstrap data)
curl -s https://example.com/some-page | grep -oE '(data-page|__NEXT_DATA__|__NUXT__)[^>]{0,200}'
```

Also run the project's own type checks, tests, and route listing. For leaked credentials in the repo, use a secret scanner (for example the `scanning-secrets` skill or `gitleaks`) and report only redacted output.

**9. Report.** Before writing a finding, try to disprove it: confirm the code path is reachable, the input is attacker-controlled, and no middleware, framework default, proxy, or platform setting already mitigates it. Downgrade to Risk or Needs runtime validation, or drop it, when you cannot rule these out. Then use the output contract below.

## Choosing which controls apply

Controls are tiered. Full details per control: [references/controls.md](references/controls.md).

| Tier | Applies to | Examples |
|---|---|---|
| 1. Core | Every project | AuthN, AuthZ/IDOR, password storage, input validation, injection, TLS, secrets, safe errors, security logging, data minimization |
| 2. Application safety | Most projects | Session/token lifecycle, rate limiting, race conditions and idempotency, file upload, DB privileges, backup/restore, client-side data exposure |
| 3. Hardening | When the feature exists | CSRF (cookie auth), CORS, security headers, SSRF (URL fetch/webhooks), encryption at rest, DoS limits |
| 4. Operational | Maturity | Dependency/supply chain, security testing, admin MFA, audit trail, incident response, privacy/retention |

Decision rules:
- Skip a control only when it is **clearly** not applicable (no uploads, no cookies, no outbound fetch). When in doubt, assume it applies and check.
- Items marked **(SPA)** apply to any project with client-side rendering or hybrid SSR/SPA (Inertia, Next.js, Nuxt, SvelteKit, Angular, React, Vue, Svelte). Skip them only when nothing is rendered client-side.
- Treat secrets embedded in mobile apps, desktop apps, browser extensions, and frontend bundles as public.

## Framework adaptation

Do not audit by matching framework names against a checklist. First infer the actual security mechanisms from the codebase, then map the general controls onto that stack's conventions. Framework knowledge is a hint for where bugs tend to hide, not a requirement list. For prompts on where to look per surface (integrations, background work, multi-tenant, admin), read [references/risk-lens.md](references/risk-lens.md) during steps 3 to 7.

## Output contract

Always use this structure for each finding:

```text
Severity: Critical | High | Medium | Low
Status: Confirmed | Risk | Needs runtime validation
Evidence: file:line or command/result
Impact: what can go wrong
Fix direction: what to change at a high level
Validation: command or manual check
```

Order findings by severity. End the report with:
- **Already good / no issue found**: controls checked and passed.
- **Not checked**: areas intentionally skipped or unavailable, with the reason.

For a hardening plan instead of an audit, group the same controls by tier and list for each: current state, gap, and the next concrete step.

## Common pitfalls

- Reporting "missing CSP" or "no rate limit" without checking the reverse proxy, CDN, or platform config where it may already live. Say where you looked.
- Trusting role checks in the frontend router or hidden buttons as authorization.
- Checking that an endpoint requires login but not that the resource belongs to the caller (IDOR).
- Missing over-shared fields because only the JSON API was reviewed, not the SSR/bootstrap payload or shared global props.
- Auditing the wrong branch or environment config.

## References

- [references/controls.md](references/controls.md): full control checklist by tier. Read when assessing a specific area or writing a hardening plan.
- [references/risk-lens.md](references/risk-lens.md): cross-stack prompts for spotting risk per surface. Read while tracing entry points and flows.

## Related tools

This skill is the broad baseline. For narrower jobs, prefer the specialised tool when available:
- Reviewing only a PR or diff: Claude Code `/security-review`, or `differential-review` from [trailofbits/skills](https://github.com/trailofbits/skills).
- Dependency and supply-chain risk: `supply-chain-risk-auditor` from trailofbits/skills.
- Secrets in the repo or history: the `scanning-secrets` skill.
