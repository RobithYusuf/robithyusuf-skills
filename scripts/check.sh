#!/bin/sh
# Validasi semua skill + pindai kredensial. Dipakai oleh git hook dan CI.
#   sh scripts/check.sh            # folder kerja
#   sh scripts/check.sh --staged   # hanya yang di-stage (pre-commit)
#   sh scripts/check.sh --history  # seluruh riwayat git (pre-push / CI)
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
MODE=${1:-$ROOT}

echo "==> Validasi skill"
python3 "$ROOT/skills/creating-agent-skills/scripts/validate_skill.py" "$ROOT"/skills/*/

echo "==> Pindai kredensial ($MODE)"
python3 "$ROOT/skills/scanning-secrets/scripts/scan_secrets.py" "$MODE"

if command -v gitleaks >/dev/null 2>&1; then
  echo "==> gitleaks"
  if [ "$MODE" = "--history" ]; then
    gitleaks git "$ROOT" --redact --no-banner
  else
    gitleaks dir "$ROOT" --redact --no-banner
  fi
fi
