#!/usr/bin/env bash
set -euo pipefail

backup_path="${1:-}"
drill_url="${DRILL_DATABASE_URL:-}"

if [[ -z "$backup_path" || -z "$drill_url" ]]; then
  echo "usage: DRILL_DATABASE_URL=... restore_drill.sh backup.dump" >&2
  exit 2
fi

database_name="$(psql "$drill_url" --tuples-only --no-align --command='select current_database()')"
if [[ "$database_name" != *_drill ]]; then
  echo "refusing restore: target database must end with _drill" >&2
  exit 3
fi

pg_restore --clean --if-exists --no-owner --no-acl --dbname="$drill_url" "$backup_path"
psql "$drill_url" --set=ON_ERROR_STOP=1 --command='select version_num from alembic_version'
echo "restore drill completed for $database_name"
