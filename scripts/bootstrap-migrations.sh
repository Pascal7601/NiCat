#!/usr/bin/env bash
# Generate Django migrations for human review; DOES NOT commit or claim verification.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${DJANGO_SETTINGS_MODULE:-}" != "config.settings.local" ]]; then
  echo "Set DJANGO_SETTINGS_MODULE=config.settings.local and local database settings first." >&2
  exit 2
fi
if [[ -z "${POSTGRES_HOST:-}" ]]; then
  echo "Set POSTGRES_HOST to your local PostgreSQL instance; no SQLite migration bootstrap." >&2
  exit 2
fi
cd backend
python manage.py makemigrations accounts academics resources questions exams attempts --noinput
python manage.py makemigrations --check --dry-run
python manage.py showmigrations
cat <<'EOF'
Generated files are UNVERIFIED. Review schema and dependencies, test on disposable
PostgreSQL, then run scripts/verify-backend.sh. Only commit after all gates pass.
EOF
