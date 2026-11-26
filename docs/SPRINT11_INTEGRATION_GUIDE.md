# NiCat v1.2 — Sprint 11 integration guide

**Scope:** Additive original-text contribution intake and two-person review. Student content is private and never used as Tutor source. Source model was checked against NiCat v0.4; compare all references against your current branch because later Sprint 6–9 changes are not fully available here.

## 1. Apply the new-files-only patch

```powershell
cd D:\Desktop\Projects\NiCat
git status --short
$patch = "$HOME\Downloads\NiCat_v1.2_Sprint11_New_Files_Only.patch"
git apply --check $patch
git apply $patch
```

The patch creates `backend/apps/contributions`, a text-only Next.js `/contribute` page, tests and docs. It does **not** overwrite your existing apps, settings, URLs or BFF code. If the patch conflicts with existing files, investigate without forcing.

## 2. Register Django app, flag and throttle

In `backend/config/settings/base.py` add ONCE inside `INSTALLED_APPS`:

```python
"apps.contributions.apps.ContributionsConfig",
```

After `REST_FRAMEWORK` is initialized, add:

```python
NICAT_CONTRIBUTIONS_ENABLED = os.environ.get("NICAT_CONTRIBUTIONS_ENABLED", "false").lower() == "true"
NICAT_CONTRIBUTION_DAILY_LIMIT = int(os.environ.get("NICAT_CONTRIBUTION_DAILY_LIMIT", "3"))
REST_FRAMEWORK.setdefault("DEFAULT_THROTTLE_RATES", {})["contribution_submissions"] = "6/hour"
```

In `backend/config/urls.py`, once inside `urlpatterns`:

```python
path("api/v1/", include("apps.contributions.urls")),
```

## 3. Strict BFF allowlist — JSON only

In `frontend/lib/route-policy.mjs`, **after** the `ALLOWED` object declaration (same integration style as the Tutor and study_coach rules):

```js
ALLOWED.GET.push(/^\/contributions\/$/, /^\/contributions\/units\/$/);
ALLOWED.GET.push(new RegExp(`^/contributions/${U}/$`));
ALLOWED.POST.push(/^\/contributions\/$/);
ALLOWED.POST.push(new RegExp(`^/contributions/${U}/withdraw/$`));
```

Your existing BFF handles JSON requests up to 22,000 characters; this release's text limit is 6,000. **Do not allow multipart file uploads through the existing text-only proxy.** Sprint 12 will need a dedicated safe multipart proxy with size limits and private storage.

## 4. Test against the correct DB

Use development PostgreSQL connection settings, not the SQLite fallback. Check first:

```powershell
python backend/manage.py shell -c "from django.db import connection; print(connection.vendor, connection.settings_dict['NAME'])"
python backend/manage.py showmigrations contributions
python backend/manage.py migrate --plan
python backend/manage.py migrate contributions
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
```

If `makemigrations --check` reports a schema mismatch, stop and reconcile the migration with the actual models. Never `--fake` a migration to silence errors.

Enable ONLY in private dev/staging:

```powershell
$env:NICAT_CONTRIBUTIONS_ENABLED = "true"
$env:NICAT_CONTRIBUTION_DAILY_LIMIT = "3"
python backend/manage.py runserver
```

Frontend:

```powershell
cd frontend
node --test tests/contributions-route-policy.test.mjs
npx tsc --noEmit
npm run build
npm run dev
```

Backend:

```powershell
python -m pytest -q backend/tests/test_contributions.py
python -m pytest -q backend/tests/test_beta_guard.py backend/tests/test_study_coach.py backend/tests/test_study_tutor.py backend/tests/test_ai_marking.py backend/tests/test_reviewer_workflow.py backend/tests/test_contributions.py
```

## 5. Django Admin reviewer roles & workflow

At `http://localhost:8000/admin/` → Groups, set up TWO different staff users:

- **Rights Reviewer**: `contributions.view_contribution`, `contributions.change_contribution`, and `contributions.review_contribution_rights`.
- **Academic Reviewer**: `contributions.view_contribution`, `contributions.change_contribution`, and `contributions.review_contribution_content`.
- Audit viewer can have `contributions.view_contributiondecision` only.

Review process: **Contributions → open item → enter and SAVE Rights review note (15+ chars) → select item in list → action Clear rights**. Then the distinct academic reviewer opens the item, enters and SAVES Academic review note, returns to list and uses **Academically approve**. The backend enforces distinct people and records decisions. Selecting an action without saved note refuses to proceed. Do not grant student accounts Django Admin access.

`approved` is NOT published. This release contains no public download/GET-body API and no Tutor source indexing. If a contributor withdraws, it becomes `withdrawn`; later Sprint 13 must also invalidate public/indexed material after publication is implemented.

## 6. Acceptances & known limitations

- Another authenticated student gets `404` for the submission detail and withdrawal; history is owner-filtered.
- A student cannot approve/reject content via API.
- Submissions are JSON-only, and the 6,000-character limit is inside the existing BFF request-size cap.
- Duplicate detection is exact normalized-text SHA-256 only. Near-duplicate detection arrives later.
- Flag off: endpoints return 404, preserving current CAT behavior.
- No public content publication/credit reward; checked authorship is a declaration, NOT a legal determination.
- With no production/staging repo available here, these are implementation files **not a claim of passing the full Django suite**. Test on your local branch before using with real student data.
