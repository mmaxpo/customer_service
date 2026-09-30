#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required" >&2
  exit 2
fi

backup_path="${1:-}"
if [[ -z "$backup_path" ]]; then
  echo "usage: backup_postgres.sh /absolute/path/backup.dump" >&2
  exit 2
fi

umask 077
pg_dump --format=custom --no-owner --no-acl --file="$backup_path" "$DATABASE_URL"
pg_restore --list "$backup_path" >/dev/null
echo "verified PostgreSQL backup: $backup_path"
