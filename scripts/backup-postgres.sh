
#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env.production ]]; then
    echo "Missing .env.production" >&2
    exit 1
fi

umask 077

mkdir -p backups

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

output="backups/nicat_${timestamp}.dump"
partial="${output}.partial"

trap 'rm -f "$partial"' EXIT

compose=(
    docker compose
    --env-file .env.production
    -f compose.prod.yaml
)

# Produce a PostgreSQL custom-format backup.
"${compose[@]}" exec -T db sh -ec \
    'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner' \
    > "$partial"

# Reject empty or invalid archives.
test -s "$partial"

"${compose[@]}" exec -T db \
    pg_restore --list < "$partial" > /dev/null

mv "$partial" "$output"

trap - EXIT

echo "Backup created: $output"
echo "IMPORTANT: This archive is not encrypted."
echo "Copy it securely to protected off-server storage."