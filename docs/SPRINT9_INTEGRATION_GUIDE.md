# NiCat v1.1 Sprint 9 — Integration and verification guide

## 1) Apply ADDITIVE new files only

The patch adds a new Django `beta_guard` app (no models or migrations), tests, docs and an authorized-only probe. It does not change the existing grading, Tutor, sources, follow-up or BFF code.

```powershell
cd D:\Desktop\Projects\NiCat
git status --short
$patch = "$HOME\Downloads\NiCat_v1.1_Sprint9_New_Files_Only.patch"
git apply --check $patch
git apply $patch
```

If you already created files with these paths, inspect collisions; do not force them. Review `git diff --stat` before committing.

## 2) Register one app

In `backend/config/settings/base.py`, add exactly once inside `INSTALLED_APPS`:

```python
"apps.beta_guard.apps.BetaGuardConfig",
```

**No `urls.py` change and no migration required.** The app only adds a deployment system check and a read-only management command.

In your production environment (not `.env` committed to Git), set:

```dotenv
NICAT_BETA_ENV=production
```

Use your existing `config.settings.production`; it already has a production fail-closed structure in the v0.4 baseline. Compare to the actual current repo, because deployment settings may have changed. Make sure `DJANGO_SETTINGS_MODULE=config.settings.production` is selected in the deployment process. **Do not set `NICAT_BETA_ENV=production` during ordinary local mock testing.**

### Important limits on Sprint 8

Sprint 8 only permits `NICAT_AI_PROVIDER=mock` for new follow-up submissions. The Sprint 9 deployment check **blocks** a real-student beta configured with mock AI or live follow-ups on an unsupported provider. To release the real beta safely, leave follow-up submissions **disabled** until a separately implemented, evaluated, cost-limited real provider exists. Also remove or isolate all mock-generated content; the audit detects obvious mock placeholders but cannot prove the absence of every one.

## 3) Run tests (local)

From project root in PowerShell:

```powershell
python -m pytest -q backend/tests/test_beta_guard.py
python -m pytest -q backend/tests/test_study_coach.py backend/tests/test_study_tutor.py backend/tests/test_ai_marking.py backend/tests/test_reviewer_workflow.py
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
```

Frontend (assuming your Sprint 6–8 BFF route rules remain integrated):

```powershell
cd frontend
node --test tests/sprint9-security-route-policy.test.mjs
node --test tests/study-coach-route-policy.test.mjs
npx tsc --noEmit
npm run build
cd ..
```

If the 6 Sprint 9 backend checks + 23 earlier tests all pass, you will have **29 selected passing tests**; your current repo may contain additional cases. A green suite is necessary, not sufficient, for beta.

Optionally run the automated, fail-fast local checks:

```powershell
.\scripts\sprint9_release_gate.ps1
```

This script runs existing regression tests and frontend build checks, but does **not** perform a production deploy check or use production secrets.

## 4) Rehearse the audit on local PostgreSQL

Preserve the same `POSTGRES_*` environment variables you used for Sprint 7–8 before running against the intended development database.

```powershell
python backend/manage.py shell -c "from django.db import connection; print(connection.vendor, connection.settings_dict['NAME'])"
python backend/manage.py nicat_beta_audit --with-db
```

This will intentionally warn that the environment is not production. It will report aggregate coverage of published beta exam question revisions where explanations are allowed, plus missing migrations and mock placeholders. This is **read-only**.

## 5) Production/staging gate (after actual deployment infrastructure exists)

**Do not run this against local production-like settings without real secrets/hosts/TLS config.** On the authorized staging environment with verified `config.settings.production`:

```powershell
$env:NICAT_BETA_ENV = "production"
$env:DJANGO_SETTINGS_MODULE = "config.settings.production"
python backend/manage.py check --deploy
python backend/manage.py nicat_beta_audit --with-db --strict --min-coverage 90
```

Any blocking finding means **stop** and fix the configuration/content. Django's `check --deploy` covers baseline framework safeguards; it does not prove the entire system secure. HSTS should be introduced cautiously (validate certificate and proxy first, start low, increase later); never blindly enable includeSubDomains or preload. Trust `SECURE_PROXY_SSL_HEADER` only if the reverse proxy reliably strips/overwrites incoming forwarded headers.

## 6) Low-volume, permissioned staging probe (optional)

For a staging account you control, set a short-lived test token in the environment (never paste or commit it):

```powershell
$env:NICAT_PILOT_BEARER_TOKEN = Read-Host "Staging bearer token"
python scripts/sprint9_probe.py --authorized --url "https://YOUR-STAGING-API/api/v1/study-coach/recommendations/" --requests 20 --workers 2
Remove-Item Env:NICAT_PILOT_BEARER_TOKEN -ErrorAction SilentlyContinue
```

Only use a hostname you own or are authorized to test. The script cannot probe arbitrary API paths, never sends POST, caps requests and concurrency, and does not print sensitive response data. The latency here is for an existing GET endpoint, **not** an end-to-end measurement of AI generation latency.

## 7) Django Admin roles before beta

- Use Groups: student (no staff), marking reviewer (`attempts.review_written_answers`), academic content reviewer (`study_tutor.approve_tutor_content`), grade correction officer (`attempts.correct_final_grades`) where supported by your current permissions, and least-privilege admin.
- Only staff reviewers can approve/withdraw source excerpts, publish Tutor explanations, publish/reject/withdraw follow-up answers. Verify negative cases with a second ordinary test user.
- Enforce MFA for staff accounts at your identity provider or admin access gateway; Django's base Admin authentication alone does not provide MFA.
- Keep copyright/rights evidence privately documented; do not treat all lecture notes as reusable by default.

## 8) Release decision

Complete the QA matrix in `docs/SPRINT9_QA_MATRIX.csv`, record reviewer approval and backup restore evidence, and sign off on the controlled pilot. Read `docs/SPRINT9_BETA_RELEASE.md` before inviting real students.

**Known limitations:** This package cannot directly inspect the user's current repo, perform security pentesting, restore a backup, validate the reverse proxy or collect real-student survey data. A passing audit is not a production certification.
