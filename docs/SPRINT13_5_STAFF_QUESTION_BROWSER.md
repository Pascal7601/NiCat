# NiCat v1.2 — Sprint 13.5: Question Browser and Tutor Review

## Purpose

Replace the human-facing `QuestionRevision` UUID entry on `/staff/tutor` with a searchable, role-gated browser. Reuse the same component on `/staff/questions` to prepare for Sprint 14's question-generation review queue. **Question generation, authoring, and exam publishing are not included.**

### User experience

1. Staff sign in at `/staff` and open **Question bank** or **AI Tutor review** in the sidebar.
2. Staff filter published questions by programme, unit, topic or free-text search.
3. NiCat only returns active **published** question revisions. Internal IDs are used only when the user selects a question; answer keys, options, rubrics, source text and student data are not serialized.
4. The Tutor page shows the chosen prompt and count of currently approved, rights-cleared excerpts aligned to its topic and unit. **This is a coverage indicator, not a guarantee** that retrieval will find matching evidence for the actual question text.
5. Clicking *Generate grounded draft* calls the **existing** `/staff/tutor/generate/` service with the selected revision ID. Existing academic reviewer permission, evidence retrieval, generation, publication and retraction rules still apply.
6. Once Sprint 14 is implemented, approved/generated-and-published question revisions automatically appear in the browser.

## Apply patch

The patch was authored against the previously supplied Sprint 12 staff workspace + staff-auth/visual fix, so inspect any conflicts with later local edits. **Commit or back up first**; do not force conflicts.

From Git Bash:

```bash
cd /d/Desktop/Projects/NiCat
git status --short
PATCH="$HOME/Downloads/NiCat_v1.2_Sprint13_5_Question_Browser.patch"
git apply --check "$PATCH"
git apply "$PATCH"
```

### Required: exact Next.js route allowlist

NiCat's BFF blocks query strings, so this browser uses a bounded, **read-only POST search** endpoint rather than uncontrolled GET query parameters. In `frontend/lib/route-policy.mjs`, insert the following **after `ALLOWED` is declared and before `permitted()`**. Do not duplicate it if it already exists:

```js
// Sprint 13.5: staff-only, read-only question discovery (JSON search body).
ALLOWED.POST.push(/^\/staff\/questions\/search\/$/);
```

Do **not** allow GET or PUT on this endpoint and do not add wildcards such as `/staff/*`. The Next.js proxy only forwards explicitly allowed JSON paths. Django checks staff permissions as well.

### No migrations and no new feature flag

Reuses the already-installed `staff_workspace` app, the `NICAT_STAFF_WORKSPACE_ENABLED` feature flag, existing question models and Tutor generation service. You **do not** need to run `makemigrations` or `migrate` for this patch.

### Staff permissions

`/api/v1/staff/questions/search/` requires an authenticated, active user with `is_staff=True` **and** both Django permissions:

- `questions.view_questionrevision`
- `study_tutor.view_tutorexplanation`

Grant these to your Academic Tutor Reviewer group via Django Admin → Authentication and Authorization → Groups. Generating and publishing Tutor drafts still additionally requires `study_tutor.approve_tutor_content` via existing services. The new `questions` capability is returned from `/staff/overview/` so only staff with the correct permissions see **Question bank** in the sidebar. Frontend visibility does not replace backend authorization.

### Test

From the repo root:

```bash
python backend/manage.py check
python -m pytest -q backend/tests/test_staff_question_browser.py backend/tests/test_staff_workspace.py backend/tests/test_study_tutor.py
cd frontend
node --test tests/staff-question-browser-route-policy.test.mjs tests/staff-question-browser-login.test.mjs
npx tsc --noEmit
npm run build
```

Then sign in with an authorized staff reviewer and visit:

- `http://localhost:3000/staff/questions`
- `http://localhost:3000/staff/tutor`

Test: ordinary student is forbidden; staff without question-view permission gets 403; filters scope to the correct programme and unit; unpublished questions are absent; option keys/rubrics are never returned; pagination is bounded; selected question creates a draft; mock content must not be published to real users.

### Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| `403` on `/questions/search/` | Missing `questions.view_questionrevision` or `study_tutor.view_tutorexplanation`, or user not active staff |
| `404 disabled` | `NICAT_STAFF_WORKSPACE_ENABLED` is false in the Django server process |
| `404` / proxy `route_not_allowed` | Missing explicit route policy `ALLOWED.POST.push` entry |
| Empty browser | No active published question revisions exist, or programme/unit filter is too restrictive. An approved uploaded PDF is **not** a QuestionRevision |
| `409 no approved sources` on draft generation | Topic-approved excerpt may not match question keywords, or rights/status changed |
| New unit not in selector | No published question has been associated with the unit yet; use the academic question bank after authoring/review |
| Tutor list empty | No Tutor explanation has been generated; this is independent of whether published question revisions exist |

### Boundaries and follow-on

- Browser uses existing published `QuestionRevision` records, not student-uploaded document text and not unpublished candidate questions.
- No answer keys, rubrics, student attempts or unreleased grading details are exposed by this new API.
- `approved_excerpt_count` reports approved, rights-allowed topic/unit evidence; the existing retrieval service re-checks relevance and rights before generation.
- This is **not** a substitute for Sprint 14's Question Candidate review queue or Sprint 15's dynamic CAT builder.
- Current filter lists have safe caps (150 programmes, 300 units/topics). Add targeted pagination and indexing as the catalogue grows.
