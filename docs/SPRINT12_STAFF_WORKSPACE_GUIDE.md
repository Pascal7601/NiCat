# NiCat v1.2 Sprint 12 — Staff & Academic Management Workspace

## What this delivers

A new `/staff` hub with four work areas: **Source library**, **Tutor explanations**, **Student contributions**, and **Follow-up reviews**. The existing `/review` written-answer marking page is linked from its navigation. Staff can register rights-unknown source documents, record evidence-backed source rights decisions, add references and topic-aligned excerpts, approve/withdraw excerpts, generate/edit/publish Tutor explanations, and perform the separate rights and academic contribution reviews.

**Safety invariants:** Existing `study_tutor.services`, `study_coach.services` and `contributions.services` remain the only authorization/business-rule paths for publishing/approving. The new workspace does not directly change exam marks, make a contribution public, or index student notes. Source rights decisions have append-only `SourceRightsDecision` audit rows. The staff API is disabled by default and all actions require explicit staff permissions. The Next.js proxy remains exact-path allowlisted. No binary uploads are included.

### 1. Apply new files (working tree unchanged files remain untouched)

```powershell
cd D:\Desktop\Projects\NiCat
git status --short
$patch = "$HOME\Downloads\NiCat_v1.2_Sprint12_New_Files_Only.patch"
git apply --check $patch
git apply $patch
```

Or extract the ZIP into a **review directory**, compare it, and copy only the new files. Never run `git apply --reject` / overwrite your existing work without reviewing conflicts. The package does not contain your current repository and should be reviewed against your branch before testing.

### 2. Wire backend (manual edits to three existing files)

In `backend/config/settings/base.py`, **once** in `INSTALLED_APPS` add:

```python
"apps.staff_workspace.apps.StaffWorkspaceConfig",
```

After the other feature flags:

```python
NICAT_STAFF_WORKSPACE_ENABLED = os.environ.get("NICAT_STAFF_WORKSPACE_ENABLED", "false").lower() == "true"
NICAT_STAFF_ALLOW_MOCK_PUBLICATION_FOR_TESTS = False
```

If your settings module does not already import `os`, add `import os`. Keep `NICAT_STAFF_ALLOW_MOCK_PUBLICATION_FOR_TESTS=False` except an explicitly isolated *synthetic-student* development database. It is *never* a production setting. The new `/staff/tutor` publish endpoint blocks literal `MOCK TEST DATA` text by default.

In `backend/config/urls.py` inside `urlpatterns` (assuming the same `include`/`path` imports as Sprint 11), add **once**:

```python
path("api/v1/", include("apps.staff_workspace.urls")),
```

### 3. Exact Next.js BFF allowlist integration

Your existing `frontend/app/api/nicat/[...segments]/route.ts` supports GET, POST and PUT only and rejects arbitrary query strings. Sprint 12 intentionally uses **GET/POST only**, with no query strings or multipart files, so **do not change that proxy**.

In `frontend/lib/route-policy.mjs`, after the `ALLOWED` object declaration and *before* `permitted()` or its final export, add:

```js
// Sprint 12 staff workspace: exact paths only. Django enforces RBAC as well.
ALLOWED.GET.push(
  /^\/staff\/overview\/$/,
  /^\/staff\/sources\/units\/$/,
  /^\/staff\/sources\/documents\/$/,
  /^\/staff\/sources\/references\/$/,
  /^\/staff\/sources\/topics\/$/,
  /^\/staff\/sources\/excerpts\/$/,
  new RegExp(`^/staff/sources/excerpts/${U}/$`),
  /^\/staff\/tutor\/$/,
  new RegExp(`^/staff/tutor/${U}/$`),
  /^\/staff\/contributions\/$/,
  new RegExp(`^/staff/contributions/${U}/$`),
  /^\/staff\/followups\/$/,
  new RegExp(`^/staff/followups/${U}/$`),
);
ALLOWED.POST.push(
  /^\/staff\/sources\/documents\/$/,
  new RegExp(`^/staff/sources/documents/${U}/rights/$`),
  /^\/staff\/sources\/references\/$/,
  /^\/staff\/sources\/excerpts\/$/,
  new RegExp(`^/staff/sources/excerpts/${U}/$`),
  new RegExp(`^/staff/sources/excerpts/${U}/action/$`),
  /^\/staff\/tutor\/generate\/$/,
  new RegExp(`^/staff/tutor/${U}/$`),
  new RegExp(`^/staff/tutor/${U}/action/$`),
  new RegExp(`^/staff/contributions/${U}/$`),
  new RegExp(`^/staff/contributions/${U}/action/$`),
  new RegExp(`^/staff/followups/${U}/$`),
  new RegExp(`^/staff/followups/${U}/action/$`),
);
```

Do **not** add a catchall `/staff/*` proxy rule. No student should receive staff content through broad route matching.

### 4. Permissions in Django Admin (one-time account setup)

Create **separate staff accounts**. Mark accounts `is_staff=True`. Django must enforce these permissions; the Next.js navigation does not grant access:

| Role | Suggested permissions |
| --- | --- |
| Source Librarian | `resources.view_sourcedocument`, `resources.add_sourcedocument`, `resources.view_sourcereference`, `resources.add_sourcereference`, `study_tutor.view_sourceexcerpt`, `study_tutor.add_sourceexcerpt`, optionally `study_tutor.change_sourceexcerpt` |
| Source Rights Officer | `resources.view_sourcedocument`, `resources.view_sourcereference`, `study_tutor.view_sourceexcerpt`, `resources.change_sourcedocument`, `staff_workspace.review_source_rights` |
| Academic Tutor Reviewer | `study_tutor.view_sourceexcerpt`, `study_tutor.approve_tutor_content`, `study_tutor.view_tutorexplanation`, and read-only `resources.view_sourcedocument` / `resources.view_sourcereference` if using the source-library page |
| Contribution Rights Reviewer | `contributions.view_contribution`, `contributions.change_contribution`, `contributions.review_contribution_rights` |
| Contribution Academic Reviewer | `contributions.view_contribution`, `contributions.change_contribution`, `contributions.review_contribution_content` |
| Follow-up Academic Reviewer | `study_coach.view_tutorfollowup`, `study_tutor.approve_tutor_content` |

For UI pages that make several read requests in parallel, grant **all listed read permissions** for that page to the staff role, or use a separate specialized staff account. Actions remain individually protected by backend permissions. Avoid superuser for routine work. **The two-person contribution separation is enforced by Sprint 11's existing service even when one person receives both permissions.**

### 5. Database migration and local activation

In the same PowerShell session used for Django, preserve your working PostgreSQL `POSTGRES_*` settings. Verify the selected DB before migrating:

```powershell
python backend/manage.py shell -c "from django.db import connection; print(connection.vendor, connection.settings_dict['NAME'])"
python backend/manage.py showmigrations staff_workspace
python backend/manage.py migrate --plan
python backend/manage.py migrate staff_workspace
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
$env:NICAT_STAFF_WORKSPACE_ENABLED = "true"
python backend/manage.py runserver
```

Enable the flag before starting Django. If the development database is SQLite because your `POSTGRES_HOST` variables weren't set, stop and reconnect to your intended PostgreSQL first. The migration creates an audit table and custom review permission; it does not alter existing question, Tutor, or contribution tables.

### 6. Tests

```powershell
python -m pytest -q backend/tests/test_staff_workspace.py
python -m pytest -q backend/tests/test_staff_workspace.py backend/tests/test_contributions.py backend/tests/test_study_coach.py backend/tests/test_study_tutor.py backend/tests/test_ai_marking.py backend/tests/test_reviewer_workflow.py
cd frontend
node --test tests/staff-workspace-route-policy.test.mjs
npx tsc --noEmit
npm run build
```

If the BFF route test fails, confirm you added the exact allowlist block above. This package's Python files have been syntax-checked and its route test validated against a reconstructed prior allowlist; it has **not** been run against your working NiCat Django database, so passing local tests is required.

### 7. End-to-end staff acceptance path

1. Sign in as an authorized source librarian; open `http://localhost:3000/staff/sources`. Register a source document and reference (rights are initially **unknown**). Select a unit and matching topic, create an excerpt. A mismatch must fail.
2. Sign in as source rights officer; review legitimate permission evidence and record an allowed/restricted decision (audit record is saved). Do **not** mark externally copyrighted or unverified material as allowed.
3. Sign in as academic reviewer; select the excerpt and approve it. Approved status is controlled by the existing `approve_excerpt()` service.
4. Open `/staff/tutor`; generate a draft for a published question revision that matches the approved topic. Review/edit the answer, common mistake and practice tip; save; then publish. Revocation of the source should prevent subsequent student retrieval.
5. Open `/staff/contributions`; save a rights rationale and clear rights as role A. Log in as role B; save an academic rationale; approve. The material remains **private**, and no `SourceDocument` or `SourceExcerpt` is automatically created.
6. Open `/staff/followups`; save a source-supported answer and publish. The existing Sprint 8 service blocks mock text or revoked citations.
7. Confirm an ordinary student is denied every `/api/v1/staff/*` endpoint, and each staff role is denied actions outside its permission set. Existing `/review` remains available through the new workspace's navigation.

### Known limitations and follow-up work

- This sprint provides **work queues**, not an entire curriculum editor or CAT exam builder. Those can be built as a later staff workspace expansion without touching Django Admin for normal reviews.
- List responses are capped (100 documents/excerpts/contributions/follow-ups; 80 Tutor explanations; 200 references; 300 topics/units) and are not paginated. Add cursor pagination before large-scale deployment.
- Rights confirmation is manually asserted by an authorized reviewer, with a rationale. It is **not proof of a legal license**. The current `SourceDocument` model has no dedicated evidence attachment; evidence should be verified separately and linked by reference where lawful.
- This sprint has no uploads, image extraction, file quarantine, or public student contribution publishing. These remain separate security-sensitive work.
- Existing Django Admin still permits privileged model edits. Production permissions should restrict direct `SourceDocument` rights changes to authorized staff, and production audit integrity should be verified across both interfaces.
- Reviewer queue access contains private student content: deploy only over HTTPS with audit logging, account controls and a privacy notice before a real pilot.
