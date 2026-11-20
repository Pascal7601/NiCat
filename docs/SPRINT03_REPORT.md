# NiCat Sprint 03 — JWT, DSA pilot, Next.js API contract

**Date:** 20 November 2026  
**Version:** 0.3 development preview  
**Implementation status:** Source changes delivered. **PostgreSQL verification and initial migration commit incomplete.**

## Delivered

1. JWT authentication via SimpleJWT: login, refresh rotation, logout refresh blacklisting, profile and registration. Session login removed from the API; the Django administration app still uses sessions/CSRF. Security and token-storage design in `JWT_AUTH.md`.
2. Content-pilot fixture authored directly from the archival DSA course outline and Searching, Sorting, Trees and Algorithms lecture notes. The 12 questions total 20 marks: 10 MCQ + 2 written, with source sections and two five-mark rubrics; not official previous examination questions. Default seed is draft; `--publish` needs staff signoff.
3. Additional API navigation: `GET /programmes/{id}/curricula/`, `GET /exams/{id}/`, and `GET /exams/?unit_id=`.
4. Typed Next.js API client, HTTP contract, provisional OpenAPI YAML, and developer reference documentation.
5. Integration tests for JWT/blacklists, academic navigation, DSA exam lifecycle and PostgreSQL concurrent submissions; added to CI gates.
6. Replaced CI's runtime `makemigrations` generation with migration drift enforcement. Added migration bootstrap and verification guides/scripts.
7. Written answer-key explanations held until grade finalization.

## Observed checks in this environment

| Test | Result |
|---|---|
| `python -m compileall -q backend` | PASS |
| `python -m unittest discover -s backend/tests -p test_domain_standalone.py` | PASS (4 / 4) |
| `tsc --noEmit --strict ... frontend-contract/nicat-api.ts` | PASS |
| Pilot JSON integrity | PASS: 12 distinct keys, 20 marks, valid correct indices and rubric sums |
| Provisional OpenAPI YAML parsing | PASS |
| Full `pytest`/Django suite | NOT RUN: Django/DRF/SimpleJWT unavailable |
| PostgreSQL 16 integration / concurrency | NOT RUN: PostgreSQL server/container unavailable |
| `makemigrations`, `migrate`, `migrate --check`, SQL review | NOT RUN: Django unavailable |
| Generated migration file git commit | NOT DONE: would be unverified |
| OpenAPI generation via drf-spectacular | NOT RUN: Django unavailable |
| Ruff and pip-audit | NOT RUN: tools/dependencies unavailable |

**Important:** Passing static and standalone checks does not prove the Django project or data migrations work. CI currently fails intentionally until reviewed migrations are generated and committed. The repository does not contain fabricated migration files.

## Mandatory acceptance before front-end integration

- Run `scripts/bootstrap-migrations.sh`, inspect generated migration files, and run `scripts/verify-backend.sh` against a disposable local PostgreSQL 16 instance.
- Resolve any failures, inspect the SQL, obtain a green PostgreSQL CI run and commit reviewed migrations.
- Compare `docs/openapi.contract.yaml` with actual drf-spectacular output; reconcile any schema differences and version as necessary.
- Have a qualified academic reviewer sign off the DSA pilot before enabling `--publish` on any shared environment.
- Keep developer JWT signing secrets out of version control; set up gateway abuse prevention and reviewer MFA before public release.

## Known engineering follow-ups

- Database triggers / protected write role for immutable published revisions and append-only audit events.
- Cross-request idempotency keys for creating attempts, prevention of accidental double-start.
- Automatic deadline finalization, robust resumability and pagination.
- More expressive answer annotations, per-criterion written grading and a second-review workflow.
- Email verification, password reset, reviewer MFA, Redis-backed throttling and Next.js BFF CSRF protection.
- Signed dependency lockfile, deployment tests, backup-restore and privacy/rights release approvals.
