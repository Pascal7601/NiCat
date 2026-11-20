# Backend architecture (2026-11-20)

```text
Next.js BFF (planned) → HTTPS Bearer JWT → Django REST API → PostgreSQL
                                           ↳ Django admin (reviewed staff only)
```

## Django module boundaries
| App | Owns |
|---|---|
| accounts | Custom User model, JWT login/refresh/logout, basic profile; Django admin sessions |
| academics | University, Programme, CurriculumVersion, CurriculumUnit, Unit, Topic |
| resources | SourceDocument, SourceReference and rights metadata |
| questions | Question, revisioned wording, rubric, option keys, review state |
| exams | ExamTemplate, version and frozen question ordering |
| attempts | Attempt, response, grading snapshots and grade history |
| analytics | Future read-only reporting, never source of canonical grades |
| common | Shared health endpoint; cross-cutting helpers |

## Invariants
- UUID primary keys; historical codes are external display metadata, never primary keys.
- Published question and exam revisions are logically immutable; any fix creates a new revision.
- One correct answer for published single-choice question; approved written rubrics sum to possible marks.
- Start attempt creates public-only and server-private snapshots, and a server-owned deadline.
- Student requests always filter by `student=request.user`; do not introduce generic arbitrary-ID lookups.
- `submit_attempt` uses row locking and `transaction.atomic` to avoid duplicate grades under PostgreSQL concurrency.
- A pending written item means no *final percentage*. Score reports must distinguish graded points and pending possible marks.
- Store UTC timestamps; front end displays Africa/Nairobi to learners.

## Architecture gaps (sprint blockers)
- Build a separate publish service with `transaction.atomic` + `select_for_update` and a two-person approval option.
- Add reviewed migrations, database constraints/triggers or API-level restricted writes to prevent bulk modification of published records.
- Reviewer-mark services exist; validate concurrency and permissions with PostgreSQL integration tests.
- Backup/restore, stricter staff permissions, uploads and object storage are future tasks.

## Written-answer grading state machine (v0.2–v0.3)

```text
Attempt: in_progress
  | POST /submit/ (atomic lock on Attempt)
  v
Attempt: grading_pending     GradeItem: pending_review
  | reviewer MARK (atomic lock on Grade, append GradingEvent)
  |   recompute scored/ungraded totals from all items
  |   repeat until all written answers finalized
  v
Attempt: graded_final        GradeItem: final
  | designated correction reviewer CORRECTS with reason
  |   recompute totals, append correction GradingEvent
  v
Attempt: graded_final        GradeItem: final (corrected)
```

### Concurrency and trust boundaries

- Student mutations lock `Attempt`; reviewer mutations lock `Grade`, making each set of calculations serial within its own phase on PostgreSQL. The state machine disallows marking before submission and disallows saving answers once submitted.
- `private_key_snapshot` contains answer keys, archived rubrics and explanations; it is **server-only**. Student API responses use `public_snapshot` and never serialize private fields. Reviewers receive only written-answer rubrics with staff permission.
- All published question and exam versions have model-level guards. Direct SQL and bulk ORM writes can bypass them; PostgreSQL immutability triggers or a protected owner role are **required before launch**.
- Audit events are currently application-enforced, not guaranteed append-only at the database layer. A DB-level audit design is an open release gate.

## Phase 2 v0.3: integration boundaries

- Django REST Framework accepts bearer JWTs via SimpleJWT. The admin site's session cookies remain protected by CSRF middleware.
- `docs/API_CONTRACT_V1.md` is the current external interface; `frontend-contract/nicat-api.ts` provides typed Next.js server-side calls.
- `seed_dsa_pilot` creates archived-source-backed, independently authored questions as drafts; publication is opt-in with reviewed staff identity.
- No published question keys are sent in active attempt payloads, and written-answer explanations are withheld until grading is final.
- PostgreSQL migration generation and suite execution are blocked in the current artifact environment; perform local/CI verification before deploying.
