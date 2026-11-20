# Next NiCat engineering tasks

The product owner approved all recommended **directional** decisions on 20 Nov 2026; the academic/legal verification gates remain outstanding.

| Issue | Priority | Workstream | Acceptance |
|---|---|---|---|
| P2-01 | P0 | Backend | Run starter on PostgreSQL 16 and fix issues; obtain green check/test/schema report |
| P2-02 | P0 | Backend | Generate, review, commit initial migrations; `makemigrations --check --dry-run` passes |
| P2-03 | P0 | DevOps | Lock patched dependencies, reproducible builds and pre-commit; security scan |
| P2-04 | P0 | Backend+Security | Harden publishing transitions with service / transaction and DB immutability controls |
| P2-05 | P0 | Backend | Reviewer grading with audited corrections and role-separated permissions |
| P2-06 | P0 | Backend+QA | PostgreSQL concurrency/idempotency/deadline test matrix, cross-user IDOR tests |
| P2-07 | P0 | Frontend+Backend | Agree stable OpenAPI response/error format + TypeScript types |
| P2-08 | P0 | Content | Human review 10–15 questions per pilot unit; verify MMU codes and rights |
| P2-09 | P1 | Frontend | Next.js auth, catalogue, exam/resume, results and pending-grade UX |
| P2-10 | P1 | Backend | Exam history pagination and topic performance analytics |
| P2-11 | P1 | Security | Password reset/email verification, staff roles and audit changes |
| P2-12 | P1 | Platform | Backup/restore and production-ready monitoring/hosting design |

First vertical slice = one review-approved DSA quiz. Do not publicly publish content until license and academic rights issues are cleared.

## Sprint 02 checkpoint — 20 November 2026

- Implemented service-level reviewer marking and separate audited correction API (source changes only; Django tests pending).
- Implemented stricter exam-publication checks and frozen rubric/explanation snapshots.
- Added original CSRF regression tests (replaced by JWT tests in v0.3), reviewer integration tests and a PostgreSQL setup/verification script.
- **Blocking verification:** network prevented Django package installation and PostgreSQL integration; see `PHASE2_SPRINT02_REPORT.md`.

## Sprint 03 checkpoint — 20 November 2026

- Implemented SimpleJWT bearer authentication, refresh rotation/blacklist and JWT tests (not yet run against Django).
- Authored an independent DSA 12-question pilot dataset, 20 marks, 30 minutes; review-gated draft seed command and integration test provided.
- Added curriculum navigation, exam detail, filtering, current API contract and typed Next.js server client.
- Added a real PostgreSQL concurrent-submit test and a strict migration drift gate in CI.
- **Still blocked:** package installation, generated/reviewed/committed migrations, end-to-end PostgreSQL test pass, schema generation/validation and audit. Follow `docs/MIGRATIONS_AND_TESTS.md`.
