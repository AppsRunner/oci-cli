#!/usr/bin/env bash
# Wrapper invoked by the systemd service.
# Runs WAL-G base backup, then pg_dump snapshot, in sequence.
# Exit code is non-zero if either step fails; systemd records the failure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [db-backup] $*"; }

log "=== LexBangla nightly backup started ==="

log "--- Step 1/2: WAL-G base backup ---"
"${SCRIPT_DIR}/walg-backup.sh" push
log "--- Step 1/2 complete ---"

log "--- Step 2/2: pg_dump snapshot ---"
"${SCRIPT_DIR}/pgdump-snapshot.sh"
log "--- Step 2/2 complete ---"

log "=== All backup steps succeeded ==="
