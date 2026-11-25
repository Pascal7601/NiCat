# NiCat v1.1 Sprint 8 — Follow-up questions, revision priorities and free-mode limits

**Status:** New-files-only implementation package. Requires the manual integrations below and local verification. It does not change existing exam scores, staff grading services, or Sprint 7 publication rules.

## Core policy

- Student asks a follow-up **only** for their own finalized attempt, on a question with a currently published, rights-cleared Tutor explanation, and only if the exam version permits explanations.
- Mock-mode follow-up submissions create **draft placeholder responses** for academic review; they are NOT real generated educational answers.
- Academic reviewers (staff with `study_tutor.approve_tutor_content`) replace the placeholder with an evidence-supported answer, then publish through Django Admin. Unreviewed answers NEVER reach students.
- Per-student daily quota and platform daily quota use PostgreSQL row locks; requests are logged in the DB. DRF scoped throttle is an additional smoothing limit, not the main quota or a DoS defense.
- Recommendations use only the current student's finalized GradeItem scores and are *not* AI-generated. No student answers, rubrics, final exam keys, or private grade records are sent to external providers.
- **No OpenAI requests:** the code only permits `NICAT_AI_PROVIDER=mock` for follow-up creation; it fails closed otherwise. Both mock API usage and monetary spend are zero. A future real provider needs separate token and dollar budget enforcement.

## 1. Apply new files

Safely back up your work and check git status first. The zip contains the same tree as the new-files-only patch.

Git Bash, at `D:/Desktop/Projects/NiCat`:

```bash
git status --short
git apply --check "/d/Downloads/NiCat_v1.1_Sprint8_New_Files_Only.patch"
git apply "/d/Downloads/NiCat_v1.1_Sprint8_New_Files_Only.patch"
```

If you already created any of these files, inspect conflicts rather than forcing patch application.

## 2. Register Django app and URLs

In `backend/config/settings/base.py`, add once to `INSTALLED_APPS`:

```python
"apps.study_coach",
```

Add these settings AFTER the REST_FRAMEWORK dict has been created (existing base.py already imports os):

```python
NICAT_AI_FOLLOWUPS_ENABLED = os.environ.get("NICAT_AI_FOLLOWUPS_ENABLED", "false").lower() == "true"
NICAT_AI_RECOMMENDATIONS_ENABLED = os.environ.get("NICAT_AI_RECOMMENDATIONS_ENABLED", "false").lower() == "true"
NICAT_COACH_STUDENT_DAILY_LIMIT = int(os.environ.get("NICAT_COACH_STUDENT_DAILY_LIMIT", "3"))
NICAT_COACH_GLOBAL_DAILY_LIMIT = int(os.environ.get("NICAT_COACH_GLOBAL_DAILY_LIMIT", "100"))
REST_FRAMEWORK.setdefault("DEFAULT_THROTTLE_RATES", {})["coach_followups"] = "20/hour"
```

In `backend/config/urls.py`, where `/api/v1/` URLs are included, add once:

```python
path("api/v1/", include("apps.study_coach.urls")),
```

The app expects the Sprint 7 `apps.study_tutor` models and services you already installed.

## 3. Add two strict Next.js BFF allowlist rules

Your `frontend/lib/route-policy.mjs` has an `ALLOWED` dict and a `U` UUID regex (as in Sprint 7). Add these **after ALLOWED has been declared**:

```js
ALLOWED.GET.push(new RegExp(`^/study-coach/attempts/${U}/questions/${U}/followups/$`));
ALLOWED.POST.push(new RegExp(`^/study-coach/attempts/${U}/questions/${U}/followups/$`));
ALLOWED.GET.push(/^\/study-coach\/recommendations\/$/);
```

Do not allow wildcard proxy routes. The Django view independently enforces authentication, ownership and release rules.

## 4. Add follow-up form to the already working Tutor explanation component

In `frontend/components/StudentTutorExplanation.tsx`, add import:

```tsx
import StudentTutorFollowUps from "@/components/StudentTutorFollowUps";
```

Place the new component INSIDE the existing `opened && data` section, after the approved citations `<ul>` and before its closing `</section>`:

```tsx
<StudentTutorFollowUps attemptId={attemptId} questionId={questionId} />
```

This makes the form available **only after** an approved Tutor explanation has successfully loaded. The student never sees it on an unfinished exam.

A new page is also available at `http://localhost:3000/revision` after integrating and running the frontend. Consider adding a normal navigation link to it from your results dashboard later.

## 5. Configure for mock testing, using the CORRECT database

In the same PowerShell terminal that starts Django:

```powershell
$env:NICAT_AI_PROVIDER = "mock"
$env:NICAT_AI_TUTOR_ENABLED = "true"
$env:NICAT_AI_FOLLOWUPS_ENABLED = "true"
$env:NICAT_AI_RECOMMENDATIONS_ENABLED = "true"
$env:NICAT_COACH_STUDENT_DAILY_LIMIT = "3"
$env:NICAT_COACH_GLOBAL_DAILY_LIMIT = "100"
Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
```

Your local.py defaults to SQLite, but your development admin has used Docker PostgreSQL. Preserve the proper `POSTGRES_*` environment variables when running migration and server. Confirm Django is connected to the intended local development DB before applying migrations:

```powershell
python backend/manage.py shell -c "from django.db import connection; print(connection.vendor, connection.settings_dict['NAME'])"
python backend/manage.py showmigrations study_tutor
python backend/manage.py showmigrations study_coach
python backend/manage.py migrate --plan
python backend/manage.py migrate study_coach
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
```

If `makemigrations --check` reports a mismatch, STOP and check your model and migration history; do not use `--fake` or drop tables. Back up relevant local records before migration.

## 6. Run tests

```powershell
python -m pytest -q backend/tests/test_study_coach.py backend/tests/test_study_tutor.py backend/tests/test_ai_marking.py backend/tests/test_reviewer_workflow.py
cd frontend
node --test tests/study-coach-route-policy.test.mjs
npx tsc --noEmit
npm run build
```

**I could check Python syntax for this downloaded patch, but could not run these against your live NiCat repo.** Use any failures to align the patch with local model/fixtures changes.

## 7. Browser end-to-end checks

1. Restart backend with correct DB and flags: `python backend/manage.py runserver`.
2. In another terminal, run `npm run dev` in frontend.
3. Sign in as a test student with a **finalized practice CAT** that has a published Sprint 7 explanation.
4. Open `/results/<attempt_id>`, then click **Explain this answer**.
5. Under the approved explanation, use **Ask a follow-up question**. Enter at least 12 characters, then submit.
6. The student sees status `draft`. **No answer is published.**
7. Sign in as an academic reviewer in Django Admin: `/admin/study_coach/tutorfollowup/`.
8. Open the draft, replace its `MOCK TEST DATA` placeholder with a factual, evidence-grounded answer (50–4000 chars), save, select it in the list, then run `Publish reviewed answers`.
9. Switch back to the student. Click **Refresh responses**. The reviewer-approved answer and approved citations are visible.
10. Visit `/revision` to see topic priorities from your finalized CATs. Retake practice questions to observe changes.
11. Try creating four questions in a day with the default limit of 3. Fourth should receive 429; quota counts survive application restarts.
12. Check another student's attempt: response should be 404. Withdraw the Tutor excerpt or revoke source rights: follow-up published content must become unavailable.

## API contract

- `GET /api/v1/study-coach/attempts/<attempt_id>/questions/<attempt_question_id>/followups/` -> student-only history; never exposes drafts.
- `POST` same path, `{"question": "..."}` -> 201 pending review / 400 invalid / 404 no ownership / 409 locked / 429 limited.
- `GET /api/v1/study-coach/recommendations/` -> student's topic-level performance priorities; only finalized results.
- Admin: `/admin/study_coach/tutorfollowup/` -> reviewer-edit, publish/reject/withdraw controls.

## Sprint 8 acceptance checks

- No paid API requests in mock mode.
- New follow-up stored as draft; only explicit human-review action publishes an answer.
- Mock placeholder cannot be published, even by a reviewer, unless rewritten with supported content.
- Released students only see their own approved answers after source rights validation.
- DB quotas apply per user and across platform daily; DRF throttle is defense in depth, not strict quota.
- Recommended topics are ranked by actual finalized marks, **never** by model hallucinations.
- Existing Sprint 6 and 7 workflows still pass.

## Security and production notes

- Do not put `OPENAI_API_KEY` in frontend variables, commits, or code.
- Do not publicly expose mock-filled test records or give real students access to the mock test deployment.
- In production, create an independent provider integration and financial usage ledger; operation counts alone do not represent actual tokens or cost.
- Add CSRF/auth checks via the existing Next.js BFF and Django permissions; this patch uses the same `/api/nicat` helper as Sprint 7.
- Use PostgreSQL for concurrent-request quota correctness. Django/DRF cache throttling alone cannot guarantee hard limits.
- Set student-data retention and delete/correction policy before public beta.
