# NiCat changelog

## v0.2 — 2026-11-20 (engineering preview)

- Added restricted reviewer queue and transactional marking for written answers.
- Added distinct grade-correction permission with auditable old/new marks and rationale.
- Made rubric and explanation immutable in per-attempt server snapshots.
- Added exam publication checks for empty exams and duplicate question revisions.
- Reordered explicit CSRF enforcement for anonymous login and registration; added integration tests.
- Added OpenAPI annotations for reviewer endpoints.
- Added local PostgreSQL setup and verification script.
- Updated minimum Django 5.2 patch level to 5.2.19 (November 2026 security patch).

**Verification:** Python source compilation and 4 dependency-free grading tests passed.
Database migrations, Django/PostgreSQL integration tests, Ruff and schema validation
are blocked by unavailable package downloads in this workspace. This is not a deployment-ready release.

## v0.1 — 2026-11-20 (first backend starter)

- Django app boundaries, academic catalogue, question versions, exam attempts, objective grading,
  result API, Docker PostgreSQL definition, initial docs and tests.

## v0.3 — 2026-11-20

- Replaced session-based DRF API authentication with SimpleJWT bearer auth, refresh rotation and blacklist-based logout. Django admin still uses session auth.
- Added DSA pilot dataset (10 MCQ and 2 rubric-marked items, 20 marks), source references, review-gated seed command, and explicit non-official labeling.
- Added exam detail, unit-filtered exam list, and programme curricula API endpoints.
- Withheld answer explanations while a written-answer review is pending.
- Added JWT, DSA, and PostgreSQL concurrency regression tests and Next.js TypeScript client contract.
- Changed CI migration policy: it no longer auto-generates migrations; missing reviewed migrations fail the gate.
- Migration generation, PostgreSQL test execution and migration commit remain **UNVERIFIED / BLOCKED** by unavailable dependencies/database in artifact environment.

## v0.4 — 2026-11-20 (student frontend + Figma integration preview)

- Extended v0.3 in place with Next.js pages for login, registration, dashboard, exam catalogue, exam detail, timed question responses, attempt submission, and result review.
- Added a method/path allowlisted Next.js BFF with HttpOnly JWT cookies, server-side refresh rotation, exact-origin protection, and no-store response headers.
- Added local-only preview fixtures, explicitly disabled for production, and responsive styles for desktop/mobile.
- Created a native editable Figma design in the Soramap workspace, with four NiCat student-flow screens, semantic color tokens and reusable elements.
- Added `docs/FRONTEND_V0_4.md` and frontend route-policy tests.
- Backend migration review and PostgreSQL tests **remain blocked/unverified** in this environment; no green PostgreSQL run or migration commit is claimed.
