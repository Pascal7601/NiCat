# NiCat v1.1 — Sprint 7: Grounded AI Tutor + academic publication

Status: **implementation patch / integration required**. Built against the NiCat v0.4 source plus the Sprint 6 new-file patch. The user's current v1.0 checkout may have newer settings, BFF and result-page code; do not overwrite those files. The changes in this Sprint 7 download add **new files only**.

## Scope

- `apps.study_tutor`: approved topic excerpts, reviewer-gated AI draft generation, reviewed/published explanation versions, source citation metadata and fail-closed student release.
- Uses existing `resources.SourceDocument` rights statuses and `SourceReference` page/section provenance; no file-upload endpoint or unreviewed student material.
- Uses PostgreSQL full-text ranking when on PostgreSQL, with deterministic topic-scoped lexical matching for SQLite test deployments.
- Separate AI model adapter (`store=False`, JSON Schema Structured Outputs) for **drafts**; no public model generation, prompt history or student answers are sent.
- Released student explanations include only academic approved text + citations. Existing essay marks and MCQ grading are unchanged.
- Admin actions permit approving/withdrawing excerpts and publishing/withdrawing explanations. New versions require prior versions to be withdrawn.
- Frontend button `StudentTutorExplanation` requests a published explanation only on finalized results.

### Explicit v1.1 Sprint 7 boundaries

The file **does not** upload notes, automatically publish generated content, provide student follow-up chat (Sprint 8), charge for AI usage, or change grade release policies. It does not import notes from Drive. Review rights before you manually add source excerpts.

## 1. Apply new files safely

From Git Bash on `feature/v1.1-ai-foundation`, with your working deployment changes and Sprint 6 files preserved:

```bash
git status --short
git apply --check "D:\\Downloads\\NiCat_v1.1_Sprint7_New_Files_Only.patch"
git apply "D:\\Downloads\\NiCat_v1.1_Sprint7_New_Files_Only.patch"
```

No existing project files are changed by this patch. If `--check` fails, **stop** and inspect the error; do not force it. Keep existing stash backups until you have a verified commit.

## 2. Connect Django (edit *existing* files, do not replace them)

### `backend/config/settings/base.py`

Your file already imports `os`, has an `INSTALLED_APPS` list, and a `REST_FRAMEWORK` dict. Add the app to the list (once):

```python
"apps.study_tutor",
```

Then add after those existing declarations:

```python
NICAT_AI_TUTOR_ENABLED = os.environ.get("NICAT_AI_TUTOR_ENABLED", "false").lower() == "true"
NICAT_AI_TUTOR_GENERATION_ENABLED = (
    os.environ.get("NICAT_AI_TUTOR_GENERATION_ENABLED", "false").lower() == "true"
)
NICAT_AI_TUTOR_MODEL = os.environ.get("NICAT_AI_TUTOR_MODEL", "") or os.environ.get("NICAT_AI_MODEL", "")
REST_FRAMEWORK.setdefault("DEFAULT_THROTTLE_RATES", {})["tutor_drafts"] = "8/hour"
```

Sprint 6 already defines `NICAT_AI_API_KEY` on Django's backend. Do not put `OPENAI_API_KEY` in a `NEXT_PUBLIC_*` variable.

### `backend/config/urls.py`

The file already imports `include` and `path`. Add a single URL entry to the existing `urlpatterns`:

```python
path("api/v1/", include("apps.study_tutor.urls")),
```

### `frontend/lib/route-policy.mjs`

After the definition of `ALLOWED`, add these **two narrowly scoped rules**. The existing UUID regex constant `U` is present in the earlier NiCat BFF implementation:

```js
ALLOWED.GET.push(new RegExp(`^/study-tutor/attempts/${U}/questions/${U}/explanation/$`));
ALLOWED.POST.push(new RegExp(`^/study-tutor/revisions/${U}/draft/$`));
```

This is required because NiCat's Next.js BFF deliberately blocks unlisted backend routes. Do **not** add a wildcard proxy rule. Keep Sprint 6's reviewer-only AI suggestion route as-is.

## 3. Add the button on the results page

In `frontend/app/results/[id]/page.tsx`, import:

```tsx
import StudentTutorExplanation from '@/components/StudentTutorExplanation';
```

Inside `data.items.map(...)`, under each question's existing result/feedback content:

```tsx
<StudentTutorExplanation
  attemptId={id}
  questionId={item.question_id}
  released={data.status === 'graded_final'}
/>
```

Keep the existing `RequestError`, marks, correct answers, and explanation display intact. The button does not appear before final grading. **Django still enforces ownership and release independently**, so a malicious client cannot bypass it by rendering the button.

## 4. Create database schema and permissions

```bash
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
python backend/manage.py migrate
```

After migration, grant trusted academic reviewers the `study_tutor | source excerpt | May approve tutor sources and explanations` permission (codename `approve_tutor_content`) **and** Django staff / admin access. You can start with a development superuser. Keep marking and content-approval permissions separate in production.

## 5. Populate approved sources (pilot: DSA, IAP, E-Commerce)

In Django Admin:

1. Create/check `Resources -> Source documents` for a pilot unit; **only** set `rights_status=allowed` when there is documented permission covering this use.
2. Create `Resources -> Source references` specifying the source document, page and section.
3. Create `Study tutor -> Source excerpts` with the matching topic, source reference and concise evidence (30–5000 characters).
4. Select the excerpt(s) and run `Approve selected excerpts (rights checked)`. Draft or unknown-rights text cannot enter retrieval.
5. Ensure your question is a **published `QuestionRevision`** associated with the same topic. Matching is topic-scoped, not a global search across students' documents.

Neither the source document nor source URL is a public download from this API; only human-approved evidence excerpts may be shown.

## 6. Generate an internal draft and publish

For local development only, in `.env` or the backend runtime environment:

```dotenv
NICAT_AI_TUTOR_ENABLED=true
NICAT_AI_TUTOR_GENERATION_ENABLED=true
NICAT_AI_TUTOR_MODEL=your-supported-model
OPENAI_API_KEY=your-server-side-secret
```

A reviewer with the custom approval permission sends (JWT or your staff session-equivalent BFF):

```http
POST /api/v1/study-tutor/revisions/{published_question_revision_uuid}/draft/
```

The endpoint responds with a draft ID and Django Admin URL. Open that `Tutor explanation` record in admin, verify the explanation **against its actual cited source snippets**, edit as needed, and select the `Publish selected drafts after academic review` action. The publish service rejects missing, withdrawn or rights-revoked evidence. Drafts are never exposed to students.

Students on final results can then open:

```http
GET /api/v1/study-tutor/attempts/{attempt_uuid}/questions/{attempt_question_uuid}/explanation/
```

This is **the `AttemptQuestion` UUID shown as `question_id` in the results API**, not the published `QuestionRevision` UUID. Responses include the published text, topic, citation title/page/section, version and approval status. Codes: `409` for unreleased results, `404` for no published/valid explanation or an attempt the current user does not own.

**Before giving real student answers or other sensitive material to a third-party AI provider, review your notice, consent/other legal basis, processing agreements and data-handling policy.** Sprint 7 uses published question content and approved evidence, not student answers.

## 7. Verification commands

Run after adding the settings, URL, BFF and results-page integration:

```bash
python -m pytest -q backend/tests/test_study_tutor.py
python -m pytest -q backend/tests/test_ai_marking.py backend/tests/test_reviewer_workflow.py
cd frontend
npm run test:contract
npm run typecheck
npm run build
```

Tests cover: draft never public, finalization gate, ownership, source-rights withdrawal, fictitious citations, reviewer permissions and stale-citation publication failures. Some existing fixture implementations may differ from the earlier snapshot; adapt **test input payloads** to your current validation rules, never weaken production permission/marking checks to make a test pass.

## 8. Limitations and sprint acceptance

- Manually curated excerpts are the approved knowledge base for this sprint. Bulk uploads, ingestion/extraction and user contributions are **not implemented**.
- A model may write an unsupported claim even with valid citation IDs. The academic reviewer must check each factual statement before publishing.
- The code implements bounded retrieval with PostgreSQL full-text search, not embeddings or vector search.
- Need to run migration/test/build checks on the user's latest local code. This environment cannot access that checkout and does not have Django/DRF installed.
- Django Admin is used as the reviewer publication interface for this slice. A branded NiCat academic reviewer dashboard could be added later.
- Approval gating is checked on every student read, including after source-rights revocation; no unsourced fallback is shown.

**Sprint 7 is complete only once a rights-cleared excerpt is approved, a draft generated, an academic reviewer publishes it, and a student can see it after the corresponding exam is fully graded—with all above checks green.**
