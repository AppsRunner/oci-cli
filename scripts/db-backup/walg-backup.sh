#!/usr/bin/env bash
# WAL-G base backup to OCI Object Storage.
# Runs nightly via the systemd timer; also called by the postgresql
# archive_command for continuous WAL archiving.
#
# Usage:
#   walg-backup.sh            → take a base backup (BACKUP PUSH)
#   walg-backup.sh wal <path> → archive a single WAL segment
#   walg-backup.sh delete     → prune backups older than WALG_RETAIN_COUNT

set -euo pipefail

CONFIG_FILE="${LEXBANGLA_BACKUP_CONFIG:-/etc/lexbangla/db-backup.env}"

# ── helpers ──────────────────────────────────────────────────────────────────

log()  { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [walg-backup] $*"; }
fail() { log "ERROR: $*"; send_alert "$*"; exit 1; }

send_alert() {
    local msg="$1"
    if [[ -n "${ALERT_WEBHOOK_URL:-}" ]]; then
        curl -sf --max-time 10 -X POST "${ALERT_WEBHOOK_URL}" \
            -H 'Content-Type: application/json' \
            -d "{\"text\":\"[LexBangla WAL-G] FAILURE on $(hostname): ${msg}\"}" \
            || true
    fi
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

# ── load config ───────────────────────────────────────────────────────────────

[[ -f "${CONFIG_FILE}" ]] || fail "Config file not found: ${CONFIG_FILE}"
# shellcheck source=/dev/null
source "${CONFIG_FILE}"

# Re-expand variables that reference other variables in the config
OCI_S3_ENDPOINT="${OCI_S3_ENDPOINT:-https://${OCI_NAMESPACE}.compat.objectstorage.${OCI_REGION}.oraclecloud.com}"
export AWS_ENDPOINT="${OCI_S3_ENDPOINT}"
export AWS_REGION="${OCI_REGION}"
export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY
export AWS_S3_FORCE_PATH_STYLE="${AWS_S3_FORCE_PATH_STYLE:-true}"
export WALG_S3_PREFIX
export WALG_COMPRESSION_METHOD="${WALG_COMPRESSION_METHOD:-brotli}"
export WALG_DELTA_MAX_STEPS="${WALG_DELTA_MAX_STEPS:-5}"
export PGHOST PGPORT PGUSER

WALG_RETAIN_COUNT="${WALG_RETAIN_COUNT:-7}"

require_cmd wal-g
require_cmd psql

# ── subcommands ───────────────────────────────────────────────────────────────

cmd_push_base() {
    log "Starting WAL-G base backup (DELTA if chain allows, else FULL)..."
    wal-g backup-push "${PGDATA:?PGDATA must be set}" \
        2>&1 | while IFS= read -r line; do log "$line"; done
    log "Base backup complete."

    # Prune old backups immediately after a successful new one
    cmd_delete_old
}

cmd_archive_wal() {
    local wal_path="${1:?WAL path argument missing}"
    wal-g wal-push "${wal_path}" 2>&1 | while IFS= read -r line; do log "$line"; done
}

cmd_delete_old() {
    log "Pruning: retaining last ${WALG_RETAIN_COUNT} base backups..."
    wal-g delete retain FULL "${WALG_RETAIN_COUNT}" --confirm \
        2>&1 | while IFS= read -r line; do log "$line"; done
    log "Pruning complete."
}

cmd_list() {
    wal-g backup-list --detail
}

# ── dispatch ──────────────────────────────────────────────────────────────────

SUBCMD="${1:-push}"
case "${SUBCMD}" in
    push|"")   cmd_push_base ;;
    wal)       cmd_archive_wal "${2:-}" ;;
    delete)    cmd_delete_old ;;
    list)      cmd_list ;;
    *)         fail "Unknown subcommand: ${SUBCMD}" ;;
esac
