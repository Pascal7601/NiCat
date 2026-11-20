# 04 — Draft REST API Contract

**Document ID:** NICAT-API-001 · **Version:** 0.1 · **State:** Proposed. These are design proposals, not running endpoints.

## Conventions
- Base path `/api/v1/`. Request/response JSON UTF-8; page-based or cursor pagination chosen consistently before implementation.
- Authentication: secure httpOnly cookie/session-based or JWT strategy must be finalized in ADR. For a browser-first platform, prefer secure cookies with CSRF defense; never store bearer tokens in localStorage.
- IDs UUID; timestamps ISO 8601 UTC; display in Africa/Nairobi on frontend.
- Errors follow a stable shape with `code`, `message`, `details`, `request_id`; avoid leaking internal tracebacks.
- Student resource endpoints return **only approved/published** material. Never include answer keys in pre-submission question payloads.

## Proposed endpoints

| Method | Path | Who | Intent |
|---|---|---|---|
| POST | `/auth/register/` | Public | Create student |
| POST | `/auth/login/` | Public | Authenticate |
| POST | `/auth/logout/` | Authenticated | End session |
| GET | `/me/` | Authenticated | Profile |
| GET | `/programmes/` | Public/auth (TBD) | List programmes |
| GET | `/curricula/{id}/units/` | Authenticated | Filter mapped units |
| GET | `/units/{id}/topics/` | Authenticated | List topic tree |
| GET | `/exams/` | Authenticated | List practice/mock templates |
| POST | `/exams/{id}/attempts/` | Student | Start attempt, freeze version/snapshot |
| GET | `/attempts/{id}/` | Owner/reviewer | Attempt state and response progress |
| PUT | `/attempts/{id}/responses/{question_id}/` | Owner in progress | Save/update one response |
| POST | `/attempts/{id}/submit/` | Owner in progress | Idempotent finalize and mark objective items |
| GET | `/attempts/{id}/result/` | Owner/reviewer | Status, score breakdown, explanations when allowed |
| GET | `/me/attempts/` | Student | Paginated attempt history |
| GET | `/me/performance/` | Student | Unit/topic analytics |

Admin authoring/review may start inside Django Admin; a staff REST surface is deferred until demonstrably needed.

## Example: question as seen before submission
```json
{
  "id": "question-instance-uuid",
  "type": "single_choice",
  "marks": 2,
  "topic": "Stacks",
  "prompt": "Which operation removes the top element of a stack?",
  "options": [
    {"id": "option-a", "text": "push"},
    {"id": "option-b", "text": "pop"},
    {"id": "option-c", "text": "enqueue"}
  ]
}
```
*Illustrative independently authored question, not extracted verbatim from a past paper.* No correct option is transmitted before the permitted review stage.

## Example: partial result after submission
```json
{
  "attempt_id": "attempt-uuid",
  "status": "grading_pending",
  "scored_marks": 8,
  "scored_possible_marks": 10,
  "ungraded_possible_marks": 20,
  "final_total_marks": null,
  "final_percentage": null,
  "items": [{"question_id":"q1","status":"final","awarded":2,"possible":2},
            {"question_id":"q2","status":"pending_review","awarded":null,"possible":5}]
}
```
All values are examples. API contracts will be validated with frontend/backend teams during Phase 1 review.

## Acceptance-critical API tests
1. Unauthenticated save/submit blocked. 2. Owner isolation on all attempt/results endpoints. 3. Submission with duplicate idempotency key leaves one finalization. 4. Expired attempt rejects post-deadline writes. 5. Hidden keys absent from questions response. 6. Submitted attempt cannot accept edits. 7. Score equals sum of finalized criteria; pending marks omitted from final percentage.
