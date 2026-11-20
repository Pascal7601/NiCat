# NiCat — migration and PostgreSQL verification gate

**As delivered in this ZIP:** Django dependencies and PostgreSQL aren't available in the artifact-generation environment. No Django migrations have been generated, run, reviewed or committed. **The complete PostgreSQL test suite has not passed yet.** Scripts and database tests are included for the team to run on a machine with dependencies and Docker.

## Local WSL commands

```bash
unzip NiCat_Backend_v0.3_JWT_DSA.zip
cd NiCat
cp .env.example .env
# Set strong local secrets in .env and use Docker Desktop WSL integration.
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
set -a; source .env; set +a
docker compose up -d db
# Once healthy:
bash scripts/bootstrap-migrations.sh
```

Review each generated `backend/apps/*/migrations/0*.py`: verify the custom user model is created in `accounts/0001_initial.py`, all foreign keys/constraints/indexes are expected, the source is not data-destructive, and the `rest_framework_simplejwt.token_blacklist` tables have applied migrations. For each proposed migration inspect SQL with `python backend/manage.py sqlmigrate <app> <migration_number>` (from a valid `PYTHONPATH` / working directory; easier: `cd backend && python manage.py sqlmigrate ...`). Check long-lived reference tables and cross-app dependencies.

```bash
bash scripts/verify-backend.sh
# only after all checks pass and the migration files have been reviewed:
git add backend/apps/*/migrations/ docs/MIGRATIONS_AND_TESTS.md
git commit -m "chore(db): add reviewed initial NiCat PostgreSQL migrations"
```

## Verification criteria

1. `makemigrations --check --dry-run` reports no model drift.
2. `migrate` cleanly applies to an empty, disposable PostgreSQL 16 database.
3. `migrate --check` reports no pending migrations.
4. `pytest` passes against PostgreSQL; concurrency test actually executes, not skipped.
5. Login/refresh/logout JWT and blacklist tests pass.
6. DSA draft seeding and reviewer-gated publication pass; no keys leak in attempts.
7. `ruff`, `pip check`, OpenAPI generated schema validation, and dependency audit pass.
8. CI uses committed migrations, not runtime migration generation.
9. Rollback/backups and production security checks are separately documented before deployment.

Do not apply unreviewed migrations to a production or shared database. Do not report the database work as verified until your WSL/CI output confirms it.
