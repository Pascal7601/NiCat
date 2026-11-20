# NiCat — Backend + Next.js Frontend v0.4

**NiCat** is an independent Kenyan university examination-preparation platform, beginning with BBIT at Multimedia University of Kenya. **Development starter, not a production system.** Django REST Framework serves a Next.js-compatible, JWT-authenticated API. Django admin still uses Django session authentication. Architecture: modular monolith with eight domain apps and PostgreSQL as the required test/production database.

## v0.4 additions (extend v0.3; no domain model reset)

- Next.js 16 App Router student frontend with dashboard, exams, timed attempt, results, login and registration pages.
- JWT browser-for-frontend API proxy with HTTP-only cookies, refresh rotation, exact-origin write protection and route allowlist.
- Editable Figma file in Soramap: https://www.figma.com/design/ZFkfJTgyrnFm2pkEYXWOJW
- See [frontend handoff](docs/FRONTEND_V0_4.md) for setup, known limitations and API/UI mappings.

## What's new in v0.3

- **JWT authentication** using SimpleJWT (15-minute access, 7-day rotating refresh, blacklist-on-rotation, logout invalidation of refresh tokens).
- **DSA pilot**: 12 source-traceable, independently authored questions on stacks, queues, searching, sorting, and trees. Total 20 marks; ten MCQs and two human-reviewed written items. Created as **draft by default**; explicit staff review gate for publishing.
- **Next.js API contract**: new catalogue, exam-detail and filter routes; documented API schemas; `frontend-contract/nicat-api.ts` typed client.
- **PostgreSQL gates**: concurrency test, JWT tests, seed/integration tests; CI and migration scripts set to fail if migrations were not committed and reviewed.
- **Grading security**: answer explanations withheld while written marks remain pending.

## Known verification limits

**Passed in v0.4 artifact environment:** Python source compilation, four standalone grading tests, three route-policy tests, and TypeScript syntax parsing. Full TypeScript type checking was **not run** without installed Next/React packages. DSA question-data validation was part of v0.3 work.

**Not passed / not executed here:** installing Django packages, generating and applying Django migration files, full pytest-django test suite, PostgreSQL locking tests, generating OpenAPI via DRF, Ruff and dependency audits. The environment has neither a reachable package index nor PostgreSQL/Docker. **Do not claim migration verification or Git commit from this package.** `docs/MIGRATIONS_AND_TESTS.md` explains how to complete these steps on WSL or CI.

## WSL/Docker setup

Requires Python 3.13, Docker Desktop with WSL integration, Git and network access for pip:

```bash
cp .env.example .env
# Replace the local example secrets (especially DJANGO_SECRET_KEY and JWT_SIGNING_KEY).
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
set -a; source .env; set +a
docker compose up -d db
bash scripts/bootstrap-migrations.sh   # Creates UNREVIEWED initial migrations
# Review the generated files; do not commit blindly.
bash scripts/verify-backend.sh       # Requires reviewed migrations and local PostgreSQL
cd backend
python manage.py createsuperuser
python manage.py seed_dsa_pilot      # DRAFT only
# Human academic review, then optionally:
python manage.py seed_dsa_pilot --publish --reviewer-email reviewer@example.com
python manage.py runserver
```

Check API schema at `http://127.0.0.1:8000/api/v1/docs/` and health at `/health/`.

## JWT API usage

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"student@example.com","password":"YOUR_PASSWORD"}'
# Returns access, refresh and user. Replace $ACCESS with the returned access value:
curl http://127.0.0.1:8000/api/v1/exams/ \
  -H "Authorization: Bearer $ACCESS"
```

**Security:** do not store refresh JWTs in browser localStorage. See [JWT_AUTH](docs/JWT_AUTH.md) for the recommended Next.js server-side BFF design. Login/logout passwords and tokens must never enter analytics or logs.

## Navigation

- [HTTP contract](docs/API_CONTRACT_V1.md) · [TypeScript SDK](frontend-contract/nicat-api.ts)
- [DSA pilot](docs/DSA_PILOT.md) · [Source data](data/dsa_pilot_questions.json)
- [Migration/test gate](docs/MIGRATIONS_AND_TESTS.md) · [Quality/security](docs/QUALITY_AND_SECURITY.md)
- [Architecture](docs/ARCHITECTURE.md) · [Engineering decisions](docs/DECISIONS.md) · [Changelog](CHANGELOG.md)
- [Phase 1 baseline](docs/phase1_baseline/) and [Sprint 02 baseline](docs/PHASE2_SPRINT02_REPORT.md)

### Working policy

- Archived academic documents are not an officially verified 2026 curriculum. Track source provenance.
- Do not distribute copyrighted original notes/papers until rights are cleared.
- For written assessments, no provisional percentage is presented as final.
- No published question edits in place; create a new revision when a verified correction is needed.
- Database-level immutability, MFA, password reset, Redis throttling, monitoring and deployment security hardening remain release gates.
