#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-tests}"

risks=$(
cat <<'EOF'
Security / Ownership|ownership|user_scoped|user scoped|other_user|forbidden|403|401|unauthorized|permission
Idempotency / Duplicates|idempotent|duplicate|idempotency
Concurrency|concurrent|concurrency|race|gather|parallel
Failure / Retry / DLQ|failure|failed|retry|dead_letter|dlq|backoff|recover
Validation Errors|invalid|validation|422|bad_request|malformed
Empty State|empty|missing|not_found|404|none|no_.*found
Permission Denied|permission|forbidden|unauthorized|403|401
Unavailable Agent|unavailable|away|busy|offline
Over-capacity Agent|over_capacity|capacity|max_open_tickets|workload|least_loaded
Workflow Pause / Resume|pause|paused|resume|resumed|approval|wait
External API Failure|external.*failure|provider.*error|api.*failure|timeout|permanent.*provider|transient.*provider|unavailable
EOF
)

echo
echo "============================================================"
echo "Risk Concept Coverage Counts"
echo "============================================================"

while IFS='|' read -r label pattern; do
  count=$(
    { grep -R -I --exclude-dir=__pycache__ -n -E "^(async def|def) test_.*(${pattern})" "$ROOT" 2>/dev/null || true; } \
      | wc -l | tr -d ' '
  )
  printf "%-35s %s\n" "$label" "$count"
done <<< "$risks"

echo
echo "============================================================"
echo "Detailed Test Matches"
echo "============================================================"

while IFS='|' read -r label pattern; do
  echo
  echo "============================================================"
  echo "$label"
  echo "============================================================"
  grep -R -I --exclude-dir=__pycache__ -n -E "^(async def|def) test_.*(${pattern})" "$ROOT" 2>/dev/null || true
done <<< "$risks"
