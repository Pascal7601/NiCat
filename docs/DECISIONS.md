# Architecture Decision Records — approved direction

- **ADR-001:** Modular monolith; Django ORM and services with explicit app boundaries.
- **ADR-002:** Django 5.2 LTS + DRF + PostgreSQL, subject to compatibility and patch updates.
- **ADR-003:** Next.js + TypeScript frontend consumes versioned OpenAPI; Django owns grade truth.
- **ADR-004:** Question/exam revisions and attempt snapshots are append-only after publication. **Limitation:** database-level enforcement and bulk-update safety are a follow-up; model `save` guards alone are insufficient.
- **ADR-005:** Reviewer-marked writing/code/case-study responses; objective-only auto grading initially.
- **ADR-006:** Reference/document licensing restricts public verbatim reproduction.
- **ADR-007 (approved default):** Same-site authenticated session cookies and CSRF, protected login/register endpoints, single origin proxy.
- **ADR-008:** Academic catalogues versioned independently of historical archive folder names.
- **ADR-009:** Server-side timers and transactional idempotent finalization; saved pre-deadline work may be finalized after deadline.

Review every new ADR as a separate markdown file before introducing irreversible API/data behavior.

## ADR-010 — JWT replaces ADR-007 for the REST API (approved change, 20 Nov 2026)

**Decision:** The product owner explicitly requested JWT. JWT bearer tokens (SimpleJWT) protect Django REST API endpoints. Django admin keeps Django's normal session/CSRF flow. Access tokens expire in 15 minutes, refresh tokens rotate and are blacklisted; logout invalidates the provided refresh token, but not outstanding short-lived access tokens. Next.js is recommended to act as a BFF and hold refresh credentials in server-side HttpOnly cookie storage. Browser-side localStorage for refresh tokens is prohibited.

**Consequences:** ADR-007 is superseded **for the REST API only**; no same-site session-based API login. Refresh-token tables add dependency on `rest_framework_simplejwt.token_blacklist` migrations. CSRF is required on any cookie-authenticated Next.js BFF mutations. Gateway throttling and reviewer MFA are release gates.
