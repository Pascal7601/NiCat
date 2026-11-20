# Testing, security, privacy & engineering quality

## Minimum checks
1. Python syntax compilation: `python -m compileall backend`.
2. Pure grading regression suite: `python backend/tests/test_domain_standalone.py` (no Django dependency).
3. Django tests: `pytest -q` with PostgreSQL (`POSTGRES_HOST` configured).
4. Django `check` and `spectacular --validate` for OpenAPI.
5. Ruff lint, dependency scanner (pip-audit), sensitive-response & IDOR integration cases.
6. Production `check --deploy`, access log review, JWT refresh revocation and BFF CSRF enforcement tests before launch.

## Known security/quality limits
- This is a developer starter, not a production app. No proof of live integration/CI pass until a networked install runs.
- JWT bearer auth is now used for Django API. CSRF remains critical for Django admin and any Next.js cookie-authenticated BFF state-changing endpoints.
- Model `save` guards cannot prevent `bulk_update`/direct SQL modifications. Restrict authoring permissions and implement DB-level immutable revision protection.
- Reviewer endpoints and audited grading services exist in source but need PostgreSQL integration verification.
- Rate limiting is process/cache-specific in development and not an abuse-prevention substitute. Use shared Redis and proxy limits before deployment.
- Runtime deployment must be configured with unique secrets, PostgreSQL credentials, TLS and private object storage. Example passwords are development-only.
- No public redistributions of archival third-party books or restricted papers.
- No official MMU affiliation implied. Compliance with Kenya Data Protection Act requires pre-launch review, not just a note in the README.

## Release gates
Approved data governance, source licensing, rights/access/deletion flows; two-person content review for high-risk items; typed API and E2E contracts; backup restore drills; dependency lock; threat model; accessibility testing; load and concurrent-submit testing; infrastructure monitoring.
