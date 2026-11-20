# NiCat — Phase 2, backend hardening sprint 02

**Date:** 20 November 2026  
**Release:** `v0.2` (development preview)  
**Status:** Source changes complete; Django/PostgreSQL verification pending a networked development environment.

## Why this sprint

The v0.1 backend starter supported objective marking but left written answers in `grading_pending` indefinitely. Its question/answer revision publication guards applied at model level only, and empty exams could be marked published. This sprint addresses reviewed marking, immutability of grading evidence, and security contract tests.

## Shipped changes

1. **Reviewer role separation** using two Django model permissions on `GradeItem`:
   - `attempts.review_written_answers`: read pending queue and give one-time first marks.
   - `attempts.correct_final_grades`: make explicitly audited corrections after finalization.
   Both also require `is_staff=True` and `is_active=True`. Grant permissions to named reviewer and correction groups in Django Admin.
2. **Transactional grading** locks the parent `Grade` row (`SELECT FOR UPDATE` on PostgreSQL), preventing concurrent adjustments to the same attempt. Awards are checked against `[0, possible_marks]` using `Decimal`, not float.
3. **Read-only student results while pending** continue to expose `final_percentage=null`. Once all pending items are reviewed, the attempt becomes `graded_final`.
4. **Grade correction audit** stores actor, reason, old and new marks, and timestamp in append-only application workflow events. Database-level event append-only enforcement still requires additional work.
5. **Reviewer-specific endpoints** (see `CONTRACT.md`). No answer key is exposed through the student attempt endpoint or reviewer queue.
6. **Question-time snapshots** now freeze the rubric for the reviewer and the explanation for results, preventing later content edits from affecting an existing attempt.
7. **Exam publication checks** prevent publishing empty exams and duplicated question revisions, and recheck unit membership.
8. **CSRF decorator order reviewed and altered** to enforce anonymous registration/login; security regression tests included, not yet executed against Django.
9. **Updated Django security lower bound** to `Django>=5.2.19,<5.3`, aligned to the official 3 November 2026 security release.
10. **Local verification script** (`scripts/verify-backend.sh`) to set up and test against PostgreSQL on a networked WSL/Linux/macOS machine.

## Routes added

| Method | Route | Required permission | Description |
|---|---|---|---|
| GET | `/api/v1/review/pending/` | `attempts.review_written_answers` | Pending queue (up to 100) with frozen rubric and submitted written answer |
| POST | `/api/v1/review/grade-items/{id}/mark/` | `attempts.review_written_answers` | First review; `marks_awarded`, `rationale` |
| POST | `/api/v1/review/grade-items/{id}/correct/` | `attempts.correct_final_grades` | Final grade correction; `marks_awarded`, `reason` |

All reviewer routes require active, authenticated staff as well as explicit model permission. API errors: 400 validation, 403 authorization, 404 missing item, 409 stale state/duplicate marking.

## Verification matrix

| Check | Observation |
|---|---|
| Python syntax compileall | **PASS**, locally executed |
| Standalone grading tests | **4/4 PASS**, locally executed |
| Reviewer-grade API integration tests | Added, **NOT RUN** (Django unavailable) |
| CSRF and exam-publication API integration tests | Added, **NOT RUN** |
| PostgreSQL migration generation and application | **NOT RUN** (dependencies/download unavailable) |
| PostgreSQL concurrency / isolation | **NOT RUN** |
| OpenAPI schema generation, Ruff, pip-audit | **NOT RUN** (dependencies unavailable) |

## Highest-priority follow-ups

- **P2-01 / P2-02:** On a networked machine install dependencies, generate and review *real* migrations, run PostgreSQL migrations, inspect the generated SQL, then commit migration files. CI currently generates migrations at runtime; make CI check migrations for drift only **after** reviewed files are committed.
- **P2-04:** Add PostgreSQL triggers or a carefully permissioned immutable publishing table design to prevent `bulk_update` and raw-SQL mutation of published question/exam versions and grading event logs. `save()` guards remain bypassable.
- **P2-06:** Create and execute transaction-based concurrent submission/review tests on PostgreSQL; verify CSRF regression tests pass.
- **P2-07:** Generate and review accurate OpenAPI schemas for reviewer endpoints and share contracts with Next.js team.
- **P2-08:** Review and rights-clear actual DSA/IAP/E-Commerce pilot questions. No archival PDF or historical question is publicly republished in this starter.

## Setup for a developer using WSL

```bash
unzip NiCat_Django_Backend_v0.2.zip
cd NiCat
cp .env.example .env
# Edit .env for your LOCAL PostgreSQL passwords and secrets.
bash scripts/verify-backend.sh
```

**Important:** `verify-backend.sh` does not prove the migration files have been reviewed and intentionally does not commit them. Check every file under `backend/apps/*/migrations/` before making a PR. The production `check --deploy` command deliberately logs warnings unless production variables are configured; the script treats that output as advisory.
