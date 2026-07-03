#!/usr/bin/env bash
# Daily pg_dump snapshot to OCI Object Storage with 30-day retention.
# Produces one compressed SQL dump per database, uploaded via the OCI
# S3-compatible API using the AWS CLI (which is pre-installed on OCI
# compute images alongside the OCI CLI).

set -euo pipefail

CONFIG_FILE="${LEXBANGLA_BACKUP_CONFIG:-/etc/lexbangla/db-backup.env}"

# ── helpers ───────────────────────────────────────────────────────────────────

log()  { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [pgdump] $*"; }
fail() { log "ERROR: $*"; send_alert "$*"; exit 1; }

send_alert() {
    local msg="$1"
    if [[ -n "${ALERT_WEBHOOK_URL:-}" ]]; then
        curl -sf --max-time 10 -X POST "${ALERT_WEBHOOK_URL}" \
            -H 'Content-Type: application/json' \
            -d "{\"text\":\"[LexBangla pgdump] FAILURE on $(hostname): ${msg}\"}" \
            || true
    fi
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

s3() {
    # Thin wrapper that targets OCI Object Storage via S3-compatible API
    aws --endpoint-url "${OCI_S3_ENDPOINT}" \
        --region "${OCI_REGION}" \
        s3 "$@"
}

# ── load config ───────────────────────────────────────────────────────────────

[[ -f "${CONFIG_FILE}" ]] || fail "Config file not found: ${CONFIG_FILE}"
# shellcheck source=/dev/null
source "${CONFIG_FILE}"

OCI_S3_ENDPOINT="${OCI_S3_ENDPOINT:-https://${OCI_NAMESPACE}.compat.objectstorage.${OCI_REGION}.oraclecloud.com}"
export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY

require_cmd pg_dump
require_cmd pg_dumpall
require_cmd aws
require_cmd gzip

STAGING_DIR="${STAGING_DIR:-/var/tmp/lexbangla-backup}"
mkdir -p "${STAGING_DIR}"
SNAPSHOT_DATE="$(date -u '+%Y-%m-%d')"
OBJECT_PREFIX="pgdump/${SNAPSHOT_DATE}"

# ── dump ──────────────────────────────────────────────────────────────────────

dump_database() {
    local dbname="$1"
    local dump_file="${STAGING_DIR}/${dbname}_${SNAPSHOT_DATE}.sql.gz"
    local object_key="${OBJECT_PREFIX}/${dbname}.sql.gz"

    log "Dumping database '${dbname}'..."
    pg_dump \
        --host="${PGHOST}" \
        --port="${PGPORT}" \
        --username="${PGUSER}" \
        --format=plain \
        --no-password \
        --verbose \
        "${dbname}" \
        2>>"${STAGING_DIR}/${dbname}.log" \
        | gzip --best > "${dump_file}"

    local dump_size
    dump_size="$(du -sh "${dump_file}" | cut -f1)"
    log "Dump size: ${dump_size} — uploading to s3://${OCI_BUCKET}/${object_key}"

    s3 cp "${dump_file}" "s3://${OCI_BUCKET}/${object_key}" \
        --storage-class STANDARD \
        --no-progress

    # Remove local staging copy once confirmed uploaded
    rm -f "${dump_file}"
    log "Upload complete: ${object_key}"
}

dump_all() {
    local dump_file="${STAGING_DIR}/globals_${SNAPSHOT_DATE}.sql.gz"
    local object_key="${OBJECT_PREFIX}/globals.sql.gz"

    log "Dumping global objects (roles, tablespaces)..."
    pg_dumpall \
        --host="${PGHOST}" \
        --port="${PGPORT}" \
        --username="${PGUSER}" \
        --globals-only \
        --no-password \
        2>>"${STAGING_DIR}/globals.log" \
        | gzip --best > "${dump_file}"

    s3 cp "${dump_file}" "s3://${OCI_BUCKET}/${object_key}" --no-progress
    rm -f "${dump_file}"
    log "Globals uploaded: ${object_key}"
}

# ── retention enforcement ─────────────────────────────────────────────────────

prune_old_snapshots() {
    local cutoff_date
    cutoff_date="$(date -u -d "-${PGDUMP_RETENTION_DAYS} days" '+%Y-%m-%d')"
    log "Pruning snapshots older than ${cutoff_date} (retention=${PGDUMP_RETENTION_DAYS}d)..."

    # List all date-prefixed folders under pgdump/ and delete any before cutoff
    s3 ls "s3://${OCI_BUCKET}/pgdump/" --recursive \
        | awk '{print $4}' \
        | grep -E '^pgdump/[0-9]{4}-[0-9]{2}-[0-9]{2}/' \
        | awk -F'/' '{print $2}' \
        | sort -u \
        | while read -r snap_date; do
            if [[ "${snap_date}" < "${cutoff_date}" ]]; then
                log "Deleting snapshot folder: pgdump/${snap_date}/"
                s3 rm "s3://${OCI_BUCKET}/pgdump/${snap_date}/" --recursive
            fi
        done

    log "Retention cleanup complete."
}

# ── manifest ──────────────────────────────────────────────────────────────────

write_manifest() {
    local manifest="${STAGING_DIR}/manifest_${SNAPSHOT_DATE}.json"
    {
        echo "{"
        echo "  \"snapshot_date\": \"${SNAPSHOT_DATE}\","
        echo "  \"hostname\": \"$(hostname)\","
        echo "  \"pg_version\": \"$(psql --host="${PGHOST}" --port="${PGPORT}" --username="${PGUSER}" -Atc 'SELECT version()' 2>/dev/null || echo unknown)\","
        echo "  \"databases\": $(echo "${PGDUMP_DATABASES}" | tr ' ' '\n' | grep -v '^$' | jq -R . | jq -s . 2>/dev/null || echo '[]'),"
        echo "  \"created_at\": \"$(date -u '+%Y-%m-%dT%H:%M:%SZ')\""
        echo "}"
    } > "${manifest}"

    s3 cp "${manifest}" "s3://${OCI_BUCKET}/${OBJECT_PREFIX}/manifest.json" --no-progress
    rm -f "${manifest}"
}

# ── main ──────────────────────────────────────────────────────────────────────

log "=== LexBangla pg_dump snapshot started (${SNAPSHOT_DATE}) ==="

dump_all

if [[ "${PGDUMP_DATABASES}" == "__all__" ]]; then
    # Full cluster dump
    full_dump="${STAGING_DIR}/cluster_${SNAPSHOT_DATE}.sql.gz"
    log "Dumping entire cluster with pg_dumpall..."
    pg_dumpall \
        --host="${PGHOST}" \
        --port="${PGPORT}" \
        --username="${PGUSER}" \
        --no-password \
        2>>"${STAGING_DIR}/cluster.log" \
        | gzip --best > "${full_dump}"
    s3 cp "${full_dump}" "s3://${OCI_BUCKET}/${OBJECT_PREFIX}/cluster.sql.gz" --no-progress
    rm -f "${full_dump}"
else
    for db in ${PGDUMP_DATABASES}; do
        dump_database "${db}"
    done
fi

write_manifest
prune_old_snapshots

# Clean up log files older than 7 days in staging
find "${STAGING_DIR}" -name "*.log" -mtime +7 -delete 2>/dev/null || true

log "=== Snapshot complete ==="
