#!/usr/bin/env bash
# Verify an existing, reviewed migration set using local PostgreSQL.
# Does not install tooling or write migrations; used after bootstrap-migrations.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${DJANGO_SETTINGS_MODULE:-}" != "config.settings.local" ]]; then
  echo 'ERROR: set DJANGO_SETTINGS_MODULE=config.settings.local (source your local .env).' >&2
  exit 2
fi
if [[ "${POSTGRES_HOST:-}" != "127.0.0.1" && "${POSTGRES_HOST:-}" != "localhost" ]]; then
  echo 'ERROR: verify script only permits local PostgreSQL host.' >&2
  exit 2
fi
mkdir -p docs/reports
python -m compileall -q backend
python -m unittest discover -s backend/tests -p 'test_domain_standalone.py'
# Explicitly require committed migration candidates: no automatic generation here.
if ! find backend/apps -path '*/migrations/0*.py' -print | grep -q .; then
  echo 'ERROR: No Django migration files found. Run bootstrap-migrations.sh and review first.' >&2
  exit 2
fi
cd backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py migrate --check
cd ..
pytest -q --cov=apps --cov-report=term-missing
ruff check backend
(cd backend && python manage.py spectacular --file ../docs/reports/openapi.generated.yaml --validate)
python -m pip check
python -m pip_audit -r requirements.txt
cat <<'EOF'
Migration and test commands completed. Review the generated SQL and source
migrations, and check database locking behavior before staging any migration
commit. Do not interpret this as a deployment security signoff.
EOF
