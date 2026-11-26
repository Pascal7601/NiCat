# NiCat v1.2 — Sprint 13: Multi-programme source document intake

**Product identity:** NiCat is an AI-powered **exam-practice platform**. Student documents are primarily evidence for **future, source-grounded question drafting**. An optional, small resource library may be introduced later and requires separate permission. **Sprint 13 does NOT generate questions or make documents public.**

## 1. What this package adds

- `apps.document_intake`: private PDF/TXT submissions, per-student history, selected programme and verified existing unit mapping, missing-unit suggestions, private original bytes, exact SHA-256 duplicate flagging, permissions for question drafting vs public resource display vs Tutor use.
- Bounded upload: maximum 8 MiB by default, file extension and PDF header / UTF-8 text checks, server-side size checks, random storage key, not publicly served.
- Separate scan/extraction worker command: `clamscan` is required; if absent, the document stays blocked from approval. `pypdf` extracts limited text from clean PDFs. No attempt to create QuestionRevision or SourceExcerpt.
- Staff review queue (`/staff/documents`) for mapping, rights clearance, independent academic approval, rights hold and rejection.
- Dedicated multipart Next.js BFF route `/api/nicat/document-upload`; the existing `/api/nicat/[...segments]` proxy remains **JSON-only**.
- Unit metadata is tied to `academics.Programme`, `CurriculumUnit` and `Unit`. No duplicate curriculum database.

## 2. Apply safely

```powershell
cd D:\Desktop\Projects\NiCat
git status --short
$patch = "$HOME\Downloads\NiCat_v1.2_Sprint13_New_Files_Only.patch"
git apply --check $patch
git apply $patch
```

The patch adds new files. It does **not** rewrite existing settings, URL registration, student sidebar, or staff sidebar. Those integration points need small manual changes as below. If a path already exists, compare it instead of overwriting.

## 3. Register Django app, flags and exact API prefix

In `backend/config/settings/base.py`, add once in `INSTALLED_APPS`:

```python
"apps.document_intake.apps.DocumentIntakeConfig",
```

After `REST_FRAMEWORK` is initialized, add once:

```python
NICAT_DOCUMENT_INTAKE_ENABLED = os.environ.get("NICAT_DOCUMENT_INTAKE_ENABLED", "false").lower() == "true"
NICAT_DOCUMENT_DAILY_LIMIT = int(os.environ.get("NICAT_DOCUMENT_DAILY_LIMIT", "3"))
NICAT_DOCUMENT_MAX_BYTES = 8 * 1024 * 1024  # Also enforced in Next.js; must not exceed 8 MiB
NICAT_DOCUMENT_PRIVATE_ROOT = os.environ.get("NICAT_DOCUMENT_PRIVATE_ROOT", str(BASE_DIR.parent / "private_document_uploads"))
REST_FRAMEWORK.setdefault("DEFAULT_THROTTLE_RATES", {})["document_uploads"] = "6/hour"
```

Ensure `base.py` already imports `os`. **Never configure `NICAT_DOCUMENT_PRIVATE_ROOT` below `STATIC_ROOT`, `MEDIA_ROOT`, or any web-served directory**, and add `private_document_uploads/` to `.gitignore` if it is under the repository. Prefer a private OS directory or mounted private volume (e.g. `D:\\NiCatPrivate\\documents`) with restricted permissions.

Inside `backend/config/urls.py` `urlpatterns`, add once:

```python
path("api/v1/", include("apps.document_intake.urls")),
```

### Database and migrations

This package intentionally has **no hand-written schema migration** because it is an additive app and your live models/migrations are not directly accessible. Generate and review the initial migration on your checked-out NiCat branch:

```powershell
python backend/manage.py shell -c "from django.db import connection; print(connection.vendor, connection.settings_dict['NAME'])"
python backend/manage.py makemigrations document_intake
python backend/manage.py migrate --plan
python backend/manage.py migrate document_intake
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
```

Confirm you are pointed at your development PostgreSQL database, not the SQLite fallback. Commit the generated migration after review. **Do not fake migrations.**

## 4. Add only exact JSON BFF allowlist entries

In `frontend/lib/route-policy.mjs`, after `ALLOWED` declaration and before `permitted()` add:

```javascript
// Sprint 13: GET/catalogue/history/staff review are JSON-only.
// Binary POST goes to the dedicated /api/nicat/document-upload/ route.
ALLOWED.GET.push(
  /^\/document-intake\/programmes\/$/,
  new RegExp(`^/document-intake/programmes/${U}/units/$`),
  /^\/document-intake\/$/,
  /^\/document-intake\/staff\/$/,
  new RegExp(`^/document-intake/staff/${U}/$`),
);
ALLOWED.POST.push(
  new RegExp(`^/document-intake/${U}/withdraw/$`),
  new RegExp(`^/document-intake/staff/${U}/review/$`),
);
```

**Do not add `POST /document-intake/` to the catchall allowlist**: that existing endpoint reads JSON and would corrupt or reject a PDF. The new explicit `frontend/app/api/nicat/document-upload/route.ts` does multipart forwarding with an 8 MiB file cap, origin checks, and HttpOnly-cookie JWT handling.

### Navigation

Add a student sidebar link in the existing `frontend/components/Shell.tsx` nav array:

```tsx
{ id: 'documents', href: '/contribute/documents', label: 'Contribute documents', icon: BookOpen },
```

If `Shell.section` is a restricted union of `'dashboard'|'exams'|'results'`, include `'documents'` in that type and change the new page's `<Shell section="dashboard">` to `<Shell section="documents">`. Keep all existing links. If your Shell is different, adapt to its current structure.

In the existing `frontend/components/staff/StaffFrame.tsx`, import `FileUp` from `lucide-react` and add to the `staffLinks` array:

```tsx
{ href: '/staff/documents', label: 'Uploaded documents', icon: FileUp, permission: 'contributions' },
```

`contributions` is the existing overview permission group. The backend separately enforces the new **document review** permissions. Staff roles who need the page may also need the existing contribution read permission to see that sidebar link. Alternatively, expose a dedicated `documents` permission flag in `/staff/overview/` in a future Staff Workspace iteration. Do not turn off backend permissions to make the tab visible.

## 5. Start services and scanning

In the **same shell in which Django runs**:

```powershell
$env:NICAT_DOCUMENT_INTAKE_ENABLED = "true"
$env:NICAT_DOCUMENT_PRIVATE_ROOT = "D:\NiCatPrivate\documents"
python backend/manage.py runserver
```

You need `pypdf` installed for clean PDFs:

```powershell
python -m pip install "pypdf>=5,<7"
```

The worker requires the **ClamAV `clamscan` executable** on PATH. Do not fake clean scans or disable malware detection to test with real documents. After setting up the scanner in the same OS/container that has access to the private root and database:

```powershell
clamscan --version
python backend/manage.py nicat_scan_documents --limit 10
```

Run the worker regularly in a **restricted**, isolated process and implement resource/CPU/memory limits before any real-student pilot. The bundled command is intended as a locally testable synchronous intake processor, not a production-grade sandbox. PDFs that are encrypted, excessively large in page count, unreadable or suspicious remain unavailable for approval. Missing ClamAV results in `processing_error` and **no approval**.

In local **synthetic test cases only**, unit tests monkeypatch the scanner to demonstrate the approval flow; that is not a safe real-document configuration.

## 6. Staff permissions and workflow

Create role-specific Django Groups/Users (active + `is_staff`):

| Role | Required new permission |
| --- | --- |
| Document catalogue mapper | `document_intake.map_document_units` |
| Rights reviewer | `document_intake.review_document_rights` |
| Academic reviewer | `document_intake.review_document_academic` |

Staff queue: `http://localhost:3000/staff/documents` (requires existing Sprint 12 staff login guard and enabled `NICAT_STAFF_WORKSPACE_ENABLED`).

1. Student uploads original document to `/contribute/documents`, selects programme and existing curriculum unit or requests an unlisted unit. File is private and `pending_scan`.
2. Worker validates with ClamAV, then extracts bounded text using `pypdf`/UTF-8. A clean file with mapped unit enters `pending_review`; otherwise it waits for verified unit mapping.
3. Mapping staff associates the document with an existing `CurriculumUnit` of the same programme, or a curriculum editor first adds a verified unit through current catalogue administration.
4. Rights reviewer checks authorship or explicit permission **for generation of questions** and records a detailed rationale.
5. **Different** academic reviewer checks the extracted concepts, academic relevance and duplication and explicitly approves; record state becomes `approved_for_questions`.
6. **No question or source excerpt is created automatically.** Sprint 14 can consume only these reviewed documents via separately verified generation jobs.

A source can be permitted for question drafting without being permitted for public downloads. `permit_resource_display` and `permit_tutor_use` are distinct optional permissions. Do not treat a student's checkbox as proof of copyright ownership.

## 7. Tests

```powershell
python -m pytest -q backend/tests/test_document_intake.py
python -m pytest -q backend/tests/test_document_intake.py backend/tests/test_staff_workspace.py backend/tests/test_contributions.py backend/tests/test_study_coach.py backend/tests/test_study_tutor.py backend/tests/test_ai_marking.py backend/tests/test_reviewer_workflow.py
cd frontend
node --test tests/document-intake-route-policy.test.mjs
npx tsc --noEmit
npm run build
```

Manual negative tests: unauthenticated upload, owner isolation, wrong programme/unit mapping, spoofed PDF, too-large files, scanner unavailable, malware detection, unreadable PDF, same-person approval, private file not downloadable, withdrawn document not entering question generation.

## 8. Known limitations / next sprint

- No near-duplicate similarity, production sandboxed PDF parsing, MIME library signature matching, OCR, public document downloads or source-grounded question generation. File magic is checked (PDF header/UTF-8) but this is **not a comprehensive file-type/security validator**. Retain quarantine and fail-closed review until additional protections pass staging testing.
- A staff-authored question and a generated question will remain separate provenance records in Sprint 14. A document approval never substitutes for validating the generated answer/rubric.
- Prototype worker runs one document at a time and does not implement a production queue or retry scheduler; for a beta use an isolated worker with per-job resource limits, retry/dead-letter handling, and private-volume controls.
- If you want to accept DOCX and PPTX later, add format-specific validation and extraction only after PDF/TXT is proven safe.
- `approved_for_questions` is *eligibility for a draft-generation job*, not public source approval and not exam question publication.
