# NiCat v1.2 — Sprint 14: Source-grounded AI Question Generation

**Status:** Additive implementation package. Syntax checked; you must test in your local NiCat repository and PostgreSQL database. The existing question model's exact *written-answer rubric contract* has not been inspected, so written candidates can be drafted/reviewed but **cannot yet be imported**. Only independently approved REAL MCQs can be imported; import also requires an explicit AI provenance value in `QuestionRevision.Provenance`. This is deliberate fail-closed behavior, not a production-complete claim.

## Purpose

Question candidates are generated from **rights-cleared, scanned, mapped, independently academically approved** `DocumentSubmission` records. The staff chooses document, topic, question type, difficulty and count. The candidate retains source hashes, evidence quotes, model/prompt version, review decision, and a link to the eventual `QuestionRevision`.

No document automatically becomes a public resource or a source for Tutor. Student access to the candidate APIs is forbidden; no answer keys are ever returned by the existing published Question Browser. The AI output is an **untrusted draft** and is only exposed to authorized reviewers.

## Install the files

From the root of your existing repository:

```powershell
cd D:\Desktop\Projects\NiCat
git status --short
$patch = "$HOME\Downloads\NiCat_Sprint14_Question_Generation_New_Files.patch"
git apply --check $patch
git apply $patch
```

The patch contains **new files only**. It intentionally does **not** rewrite `StaffFrame.tsx`, `settings/base.py`, `config/urls.py`, or your route allowlist—these have changed locally several times. If a target file exists already, review it instead of applying blindly.

## Django registration

In `backend/config/settings/base.py`, in `INSTALLED_APPS` add:

```python
"apps.question_generation.apps.QuestionGenerationConfig",
```

After your other environment flags (make sure `os` is already imported):

```python
NICAT_QUESTION_GENERATION_ENABLED = os.environ.get('NICAT_QUESTION_GENERATION_ENABLED','false').lower() == 'true'
NICAT_QUESTION_AI_PROVIDER = os.environ.get('NICAT_QUESTION_AI_PROVIDER','mock').lower()
NICAT_QUESTION_AI_REMOTE_ENABLED = os.environ.get('NICAT_QUESTION_AI_REMOTE_ENABLED','false').lower() == 'true'
NICAT_QUESTION_AI_MODEL = os.environ.get('NICAT_QUESTION_AI_MODEL','')
NICAT_QUESTION_AI_API_KEY = os.environ.get('OPENAI_API_KEY','')
```

In `backend/config/urls.py`, inside `urlpatterns` add exactly once:

```python
path('api/v1/', include('apps.question_generation.urls')),
```

Ensure the `path` and `include` imports already exist.

### Frontend BFF route allowlist

In `frontend/lib/route-policy.mjs` **after** `ALLOWED` is defined, add exactly:

```javascript
// Sprint 14 — only these staff-authenticated JSON API paths.
ALLOWED.GET.push(
  /^\/question-generation\/sources\/$/,
  /^\/question-generation\/jobs\/$/,
  new RegExp(`^/question-generation/jobs/${U}/$`),
);
ALLOWED.POST.push(
  /^\/question-generation\/jobs\/$/,
  new RegExp(`^/question-generation/candidates/${U}/edit/$`),
  new RegExp(`^/question-generation/candidates/${U}/action/$`),
  /^\/question-generation\/external-authorizations\/$/,
);
```

No wildcards, no arbitrary document fetch or file content endpoint. Avoid duplicate declarations of `U` and `ALLOWED`.

### Sidebar

In the existing `frontend/components/staff/StaffFrame.tsx`:

1. Import `Sparkles` from `lucide-react` (combine with existing icon imports).
2. Add **after Question Bank** in the existing `staffLinks` array:

```tsx
{href:'/staff/generate',label:'Generate questions',icon:Sparkles,permission:'questions'},
```

`permission:'questions'` reuses the already existing Sprint 13.5 browser visibility flag. Backend generation permissions are enforced separately. If you want a dedicated sidebar capability later, add it to `/staff/overview/` and your `StaffAccessGate` permission type.

### Django migrations

Double-check that Django is connected to the intended **development PostgreSQL** database, not the SQLite fallback:

```powershell
python backend/manage.py shell -c "from django.db import connection; print(connection.vendor, connection.settings_dict['NAME'])"
python backend/manage.py makemigrations question_generation
python backend/manage.py migrate --plan
python backend/manage.py migrate question_generation
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
```

Review and commit the generated migration. It was not bundled as handwritten SQL because your exact current model migrations are unavailable.

### Staff permissions

Grant active `is_staff=True` reviewers, preferably through separate groups:

| Role | Django permission |
|---|---|
| Generation operator | `question_generation.request_question_generation` |
| Vendor/rights reviewer | `question_generation.approve_external_question_ai` |
| Academic candidate reviewer | `question_generation.review_question_candidate` |
| Question-bank importer | `question_generation.import_question_candidate`, `questions.add_question`, `questions.add_questionrevision`, `questions.change_questionrevision` |

The person who requested a generation job **cannot** academically approve that job's candidates; the source uploader cannot approve them either. A separate rights reviewer authorizes external processing of the specific document after verifying permissions and vendor/privacy requirements.

For now the sidebar uses existing `questions` visibility, so grant `questions.view_questionrevision` and `study_tutor.view_tutorexplanation` to any generation operator you want to see that navigation item. Backend actions still use the narrower new permissions.

## Mock test mode — costs nothing

Start Django **in the same terminal** that has the flags:

```powershell
$env:NICAT_QUESTION_GENERATION_ENABLED='true'
$env:NICAT_QUESTION_AI_PROVIDER='mock'
$env:NICAT_QUESTION_AI_REMOTE_ENABLED='false'
python backend/manage.py runserver
```

In another terminal with identical Django database/settings:

```powershell
python backend/manage.py nicat_process_question_jobs --limit 3
```

The mock generates deliberately artificial candidates. They are *never* eligible for approval/import, even after manual edits. Use them only with synthetic documents/test accounts.

## Real provider — explicit opt-in only

* Do not put a key in source code or the browser. Use an environment variable on the backend worker only. Never paste keys into chat, logs, screenshots or Git.
* Install `openai` as an optional server-side dependency. The adapter uses the Responses API and parses a bounded JSON `questions` array. Its output is still subject to strict local validation and human review. Configure `NICAT_QUESTION_AI_PROVIDER=openai`, `NICAT_QUESTION_AI_MODEL=<a model supporting JSON object output>`, `NICAT_QUESTION_AI_REMOTE_ENABLED=true` only after cost and data-rights approval.
* A dedicated **Vendor/rights reviewer** must record authorization for each source under `/staff/generate`; the authorization is bound to the document SHA-256 and provider. The person requesting generation cannot authorize it. Disabling the remote flag or revoking the document blocks new and in-flight jobs.
* Uploaded notes may contain personal or protected material; perform vendor terms/privacy/data transfer assessment and redact sensitive material before enabling the real provider. A student granting *question generation* permission does not alone authorize third-party transfer.
* Set conservative account-level spending controls. `count <= 5` is a per-job bound but **not a complete monetary quota**. Do not enable remote processing for a broad pilot without per-day budgets, monitoring and a security review.

OpenAI's modern Responses API is documented at https://developers.openai.com/api/docs/guides/structured-outputs . Avoid relying on mock output as educational material.

## Local tests

```powershell
python -m pytest -q backend/tests/test_question_generation.py
python -m pytest -q backend/tests/test_question_generation.py backend/tests/test_document_intake.py backend/tests/test_staff_question_browser.py backend/tests/test_staff_workspace.py
cd frontend
node --test tests/question-generation-route-policy.test.mjs
npx tsc --noEmit
npm run build
```

`frontend/app/staff/generate/` should be visible at `http://localhost:3000/staff/generate` after Next.js restart and login. Use **synthetic original notes** for mock testing.

## Acceptance walkthrough

1. Verify a document is `approved_for_questions`, `clean`, `done`, has a verified programme/unit and two distinct reviewers.
2. Login as generation operator and select the document and a matching topic. Request 1–5 question drafts.
3. Run `python backend/manage.py nicat_process_question_jobs --limit 3` in the trusted private worker environment.
4. Refresh job history. Inspect source quotes and validation flags. In mock mode, candidates remain unpublishable.
5. In real-provider mode only, after individual vendor authorization, a *different* academic reviewer verifies each correct answer and actual source quote, edits/approves candidate, and separately an importer with the required permissions can import **MCQ** revisions.
6. Visit `/staff/questions`: an imported published MCQ should become visible in the existing question browser. `/staff/tutor` still independently requires approved Tutor excerpts.
7. Withdraw the source or revoke external authorization: queued jobs must be blocked; already generated drafts should fail publication checks. Existing exam snapshots, if any, remain immutable for audit.

## Deliberate limits / remaining integration

- **Written questions:** candidate generation and review are included. Their automatic import awaits the exact `RubricCriterion` fields and existing question-service publication contract; do not create ungradeable essays.
- **AI provenance:** MCQ import fails closed if `QuestionRevision.Provenance` lacks an AI-generated enum value. Inspect `backend/apps/questions/models.py` and add an appropriate provenance choice through the existing migrations/review process; never silently mark AI work as original student/lecturer content.
- **Content quality:** structural validation cannot prove correctness, ambiguity, difficulty or syllabus coverage. Human review and representative evaluation datasets remain mandatory.
- **External provider:** Responses API SDK behavior depends on configured model support; verify supported JSON output before enabling paid jobs. The worker must be rate-limited, isolated, and monitored.
- **Backpressure:** no automatic schedules, Redis/Celery queue, cancellation UI, or monetary budget accounting are provided in this slice. The bounded management command is a development worker. For real deployment, add recovery for stalled `running` jobs, queue concurrency protection, provider timeouts and budget alerts.
- **Security:** approval and import paths must also be protected from bypass via direct Django Admin edits. Scope model permissions appropriately; do not grant candidates to general Django Admin editors.
