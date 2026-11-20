# NiCat API contract v1 — Next.js integration

**Base URL:** `${NICAT_API_URL}/api/v1` (development: `http://127.0.0.1:8000/api/v1`). JSON over HTTPS in production. Authentication on protected endpoints: `Authorization: Bearer <access_jwt>`. No cookie session or CSRF handshake is required for direct bearer-authenticated Django API requests; **Next.js cookie-authenticated BFF endpoints must enforce CSRF defenses**.

**Status:** implemented route/serializer shape and reviewed static contract, **not yet verified by a running Django/PostgreSQL integration suite**. Machine-readable draft: `docs/openapi.contract.yaml` (hand-maintained). An authoritative generated schema will be produced by `python manage.py spectacular --file docs/reports/openapi.generated.yaml --validate` once Django can run.

## Authentication

| Method | Path | Authorization | Request | Success |
|---|---|---|---|---|
| POST | `/auth/register/` | public | `{email,password}` | `201 UserProfile` |
| POST | `/auth/login/` | public | `{email,password}` | `200 {access,refresh,user}` |
| POST | `/auth/refresh/` | public (refresh token) | `{refresh}` | `200 {access,refresh}` (old refresh revoked) |
| POST | `/auth/logout/` | Bearer | `{refresh}` | `204` (refresh revoked, access valid to expiry) |
| GET | `/me/` | Bearer | — | `200 UserProfile` |

Passwords are validated by Django. `UserProfile` includes `id`, `email`, `date_joined` only. Login credentials are rejected with 401. Invalid/expired bearer token is 401. Unauthorized staff actions are 403.

## Academic and exam catalogue

| Method | Path | Authorization | Success |
|---|---|---|---|
| GET | `/programmes/` | Public | paginated `Programme[]` |
| GET | `/programmes/{programme_id}/curricula/` | Bearer | paginated `Curriculum[]` |
| GET | `/curricula/{curriculum_id}/units/` | Bearer | paginated `CurriculumUnit[]` |
| GET | `/units/{unit_id}/topics/` | Bearer | paginated `Topic[]` |
| GET | `/exams/?unit_id={uuid}` | Bearer | paginated `Exam[]` |
| GET | `/exams/{exam_id}/` | Bearer | `Exam` |

Pagination follows DRF `{count,next,previous,results}` with default page size 20. Exam list shows **only published active exams**. Exam responses include `id, title, unit_id, duration_seconds, instructions`, **never** question answers or answer rubrics. `Curriculum.is_officially_verified` remains false for archival material.

## Attempts and results

| Method | Path | Authorization | Purpose |
|---|---|---|---|
| POST | `/exams/{exam_id}/attempts/` | Bearer | Start attempt, returns question snapshots and `deadline_at`, 201 |
| GET | `/attempts/{attempt_id}/` | Bearer, owner | Read saved attempt and remaining questions |
| PUT | `/attempts/{attempt_id}/responses/{question_id}/` | Bearer, owner | Save `{selected_option_id:uuid|null}` **or** `{text_answer:string}`; 200 `{saved_at}` |
| POST | `/attempts/{attempt_id}/submit/` | Bearer, owner | Idempotent finalization; returns `{id,status,result_url}` |
| GET | `/attempts/{attempt_id}/result/` | Bearer, owner | Grade summary, item results, explanations if final and enabled |
| GET | `/me/attempts/` | Bearer | Array of up to 50 recent attempts |

**Attempt states:** `in_progress -> grading_pending -> graded_final`, or `in_progress -> graded_final` if no pending written answers. `expired` reserved; current implementation rejects late writes but permits submission of autosaved answers after the deadline. **Auto-submit at deadline is not yet implemented.** Repeated submission returns the same finalized attempt without a second grade row. Cross-user attempt IDs yield 404.

**Question snapshots:** `id`, `position`, `kind`, `prompt`, `marks` (decimal string), `topic`, `provenance`, `options:[{id,text}]` and optional saved `response`. Pre-submission payloads omit correct answers, grading rubrics and explanations. A submitted result includes `scored_marks`, `scored_possible_marks`, `ungraded_possible_marks`, `final_percentage` (`null` while written review pending), and per-item `awarded`, `possible`, `status`, `correct_answer`/`explanation` (only after finalization if release setting allows).

**Written marking:** requires a reviewer. The student is shown `grading_pending` until all written questions are marked. There is no automatic AI grading of essays in the MVP.

## Staff-only grading

| Method | Path | Permission | Request |
|---|---|---|---|
| GET | `/review/pending/?limit=20` | `attempts.review_written_answers` + active staff | — |
| POST | `/review/grade-items/{item_id}/mark/` | `attempts.review_written_answers` + active staff | `{marks_awarded: "4.00", rationale: "..."}` |
| POST | `/review/grade-items/{item_id}/correct/` | `attempts.correct_final_grades` + active staff | `{marks_awarded: "4.50", reason: "..."}` |

Marking is row-locked, bounded by the question's maximum, and audited. The reviewer queue contains frozen rubric criteria; it is never returned to student endpoints.

## Errors

- `400` — validation errors (serializer field messages or `{code:"validation_error",message:"..."}`).
- `401` — unauthenticated / invalid JWT.
- `403` — forbidden reviewer action.
- `404` — object not found or owned by another user.
- `409` — attempt is no longer editable, result not submitted, or grading transition invalid.
- `429` — throttle exceeded.

Handle `error.detail`, `error.code`, and DRF field-error objects. Do **not** assume all failures share a single error shape; the BFF wrapper should normalize them.

## End-to-end request sequence (conceptual)

1. `POST /auth/login/` gets access/refresh; store refresh securely in Next.js server-side session or HttpOnly cookie design.
2. `GET /programmes/`, `GET /programmes/{id}/curricula/`, `GET /curricula/{id}/units/` to choose an academic unit.
3. `GET /exams/?unit_id={unitId}` lists available mock exams.
4. `POST /exams/{examId}/attempts/` starts the server-timed attempt.
5. `PUT /attempts/{id}/responses/{questionId}/` autosaves each changed answer; timer display is client-side advisory only.
6. `POST /attempts/{id}/submit/` finalizes the attempt, then `GET /attempts/{id}/result/` gets grade status.
7. If `grading_pending`, display pending state; reviewers complete their queue. Later results become final.

## Compatibility policy

Keep `/api/v1/` stable. Changes to existing response fields require a contract review and migration plan. New optional fields may be added without a new version. Use schema generation and TypeScript type check in CI once dependencies are installed. See `frontend-contract/nicat-api.ts`.
