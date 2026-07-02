#!/bin/bash
# LexBangla production health check.
# Invoked by systemd and the CD pipeline post-deploy.

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$DEPLOY_DIR/.env.prod"

BASE_URL="https://${DOMAIN}"
PASS=0
FAIL=0

check() {
  local label="$1"
  local url="$2"
  local expected_status="${3:-200}"

  STATUS=$(curl -o /dev/null -s -w "%{http_code}" --max-time 10 "$url" || echo "000")
  if [[ "$STATUS" == "$expected_status" ]]; then
    echo "  [PASS] $label ($STATUS)"
    ((PASS++))
  else
    echo "  [FAIL] $label — expected $expected_status, got $STATUS"
    ((FAIL++))
  fi
}

echo "==> LexBangla health checks ($BASE_URL)"
echo ""

check "HTTPS reachable"        "$BASE_URL/"
check "API health endpoint"    "$BASE_URL/api/health/"
check "Static assets"          "$BASE_URL/static/favicon.ico"
check "HTTP→HTTPS redirect"    "http://${DOMAIN}/"              "301"

# Check all containers are running
echo ""
echo "==> Docker container status:"
docker ps --format "  {{.Names}}: {{.Status}}" | grep lexbangla || echo "  (no lexbangla containers running)"

echo ""
if [[ $FAIL -gt 0 ]]; then
  echo "RESULT: $FAIL check(s) FAILED, $PASS passed."
  exit 1
else
  echo "RESULT: All $PASS checks passed."
fi
