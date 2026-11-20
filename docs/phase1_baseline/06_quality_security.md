# 06 — Quality, Security & Operational Standards

**Document ID:** NICAT-QA-001 · **Version:** 0.1 · **State:** Proposed engineering standard.

## Architecture quality
- Modular Django monolith, context boundaries enforced by imports/service APIs, business rules separated from views and serializers; avoid deep cross-app circular imports.
- Use a custom user model from the first migration; keep auth implementation minimal and auditable.
- Adopt a consistent formatter/linter, type checking at module boundaries, `pytest-django`, factory fixtures, API tests, and `pre-commit`.
- Code review requires issue link, threat/data implications when relevant, tests, migration review, doc changes and rollback notes.
- Dependencies locked and security-scanned in CI; isolate secrets outside source control and logs.
- Generate OpenAPI spec, validate it in CI and publish an up-to-date API reference.

## Authentication and authorization
- Auth strategy must be chosen before coding. Secure server-managed sessions / httpOnly cookies with CSRF protection fit a browser-first Next.js + Django deployment; cross-origin and deployment implications need an ADR.
- Django Admin access restricted to staff roles; separate author from approver where feasible; enforce object-level permissions in Django Admin and API.
- Sensitive operations and staff sign-ins should support MFA in a later delivery or at launch if available through selected auth provider; reviewer accounts are higher risk than student accounts.
- Enforce permissions server-side, never rely on hidden frontend controls.

## Assessment integrity
- Start/deadline/submission timestamps are server generated; store UTC.
- All marking uses frozen approved revisions; enforce max marks and permitted decimal precision; validate rubric weights.
- Use database transactions and duplicate-request handling for submit/grade; test concurrent submissions and deadline boundaries.
- Do not send private answer keys/rubrics to a client before the disclosure stage.
- Maintain grade history and audit reasons on corrections; never silently recalculate historical results after a source edit.
- For pending human review, show `pending`/`partial`; don't invent final grades.

## Kenya privacy/compliance
- Kenya's Data Protection Act, 2019 applies to personal-data handling; review controller/processor obligations, notice, retention, subject rights, transfer safeguards and ODPC registration requirements as applicable. **Do not assume registration exemption**; obtain compliance advice before launch.
- Minimize collection: email + chosen academic profile; avoid requiring university registration numbers unless demonstrably necessary.
- Ensure students can request deletion/access where required, define retention policies and backup expiration, avoid public leaderboards by default.
- Use private document storage, virus/mime/size checks, restrict upload/download authorization and avoid exposing raw Drive credentials or URLs containing tokens.

## Threat model starter
| Risk | Design mitigation | Verification |
|---|---|---|
| IDOR: view another student's result | Object ownership checks, scoped querysets | Negative integration tests |
| Answer key leak before submission | Response schema allowlist; separate secret answer storage | Contract tests / API snapshot |
| Repeated submit/double grading | Atomic transitions, unique constraints, idempotency | Concurrency test |
| Browser-clock manipulation | Server deadlines | Boundary tests |
| XSS in question HTML/markdown | Safe rendering and sanitization | Payload tests |
| Untrusted document uploads | Private storage, scanner, strict file limits | Upload abuse tests |
| Reviewer privilege escalation | Scoped Django permissions, audit trails | Permission matrix tests |
| Sensitive information in logs | Structured redaction, access-controlled observability | Logging inspection |

## Quality gates (proposed)
1. **Unit tests** for score calculations, rubric validation, attempt status, timeouts and question revisions.
2. **Integration tests** for Django API/database permissions, role boundaries, idempotency and migrations.
3. **End-to-end tests** for student completion on both desktop and mobile (Playwright).
4. **Accessibility checks** of keyboard navigation, screen-reader labels, focus and timed exam announcements.
5. **Security checks** for Django `check --deploy`, secret leakage, dependency vulnerabilities, common OWASP risks and backup restores.
6. **Operational readiness**: metrics for errors/latency/submission success, alerting on repeated grading failures and validated database backups.

## Initial performance measurements (targets, not claims)
Pilot p95 API read latency < 500 ms for typical endpoints at an agreed simulated concurrency; 0 duplicate finalized attempts across load/retry tests; recovery objectives and uptime targets to be chosen after deployment architecture is known.

## Documentation definition of done
Any change to request/response JSON, domain invariant, public route, settings, feature flag, access rule, grading logic or academic mapping requires an associated documentation update. `README` + bootstrap instructions + API schema + ADRs + decision log are version-controlled.
