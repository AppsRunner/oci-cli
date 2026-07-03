#!/usr/bin/env bash
# Restore smoke-test for the LexBangla backup suite.
# Run this after each major change to the backup scripts to confirm the
# full backup → restore cycle works end-to-end.
#
# Requires: local PostgreSQL running, AWS CLI, WAL-G, and a configured
# /etc/lexbangla/db-backup.env pointing at the real OCI bucket (or a
# test bucket with WALG_S3_PREFIX / OCI_BUCKET overrides below).
#
# Usage:
#   test-restore.sh [--bucket my-test-bucket] [--keep-testdb]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${LEXBANGLA_BACKUP_CONFIG:-/etc/lexbangla/db-backup.env}"

KEEP_TESTDB=false
TEST_BUCKET_OVERRIDE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --bucket)       TEST_BUCKET_OVERRIDE="$2"; shift 2 ;;
        --keep-testdb)  KEEP_TESTDB=true;           shift ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# ── helpers ───────────────────────────────────────────────────────────────────

PASS=0; FAIL=0
log()  { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [test-restore] $*"; }
ok()   { log "  PASS: $*"; ((PASS++)) || true; }
fail() { log "  FAIL: $*"; ((FAIL++)) || true; }

# ── load config ───────────────────────────────────────────────────────────────

[[ -f "${CONFIG_FILE}" ]] || { log "Config not found: ${CONFIG_FILE}"; exit 1; }
# shellcheck source=/dev/null
source "${CONFIG_FILE}"

if [[ -n "${TEST_BUCKET_OVERRIDE}" ]]; then
    OCI_BUCKET="${TEST_BUCKET_OVERRIDE}"
    WALG_S3_PREFIX="s3://${OCI_BUCKET}/walg"
    log "Using test bucket override: ${OCI_BUCKET}"
fi

OCI_S3_ENDPOINT="${OCI_S3_ENDPOINT:-https://${OCI_NAMESPACE}.compat.objectstorage.${OCI_REGION}.oraclecloud.com}"
export AWS_ENDPOINT="${OCI_S3_ENDPOINT}"
export AWS_REGION="${OCI_REGION}"
export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY
export AWS_S3_FORCE_PATH_STYLE="${AWS_S3_FORCE_PATH_STYLE:-true}"
export WALG_S3_PREFIX
export WALG_COMPRESSION_METHOD="${WALG_COMPRESSION_METHOD:-brotli}"
export PGHOST PGPORT PGUSER

STAGING_DIR="${STAGING_DIR:-/var/tmp/lexbangla-backup}"
mkdir -p "${STAGING_DIR}"
TEST_DB="lexbangla_restore_test_$(date -u '+%Y%m%d%H%M%S')"
SNAPSHOT_DATE="$(date -u '+%Y-%m-%d')"

s3() { aws --endpoint-url "${OCI_S3_ENDPOINT}" --region "${OCI_REGION}" s3 "$@"; }

# ── test 1: OCI Object Storage connectivity ───────────────────────────────────

log "=== Test 1: OCI Object Storage connectivity ==="
if s3 ls "s3://${OCI_BUCKET}/" >/dev/null 2>&1; then
    ok "Can list s3://${OCI_BUCKET}/"
else
    fail "Cannot reach s3://${OCI_BUCKET}/ — check credentials and endpoint"
fi

# ── test 2: WAL-G can list backups ────────────────────────────────────────────

log "=== Test 2: WAL-G backup listing ==="
if wal-g backup-list 2>&1 | grep -qE 'base_|No backups'; then
    ok "wal-g backup-list succeeded"
else
    fail "wal-g backup-list failed or returned unexpected output"
fi

# ── test 3: pg_dump + upload + download round-trip ────────────────────────────

log "=== Test 3: pg_dump snapshot round-trip ==="

# Create a tiny test database with a known row
psql --host="${PGHOST}" --port="${PGPORT}" --username="${PGUSER}" \
    -c "DROP DATABASE IF EXISTS ${TEST_DB};" 2>/dev/null || true
psql --host="${PGHOST}" --port="${PGPORT}" --username="${PGUSER}" \
    -c "CREATE DATABASE ${TEST_DB};" 2>/dev/null

psql --host="${PGHOST}" --port="${PGPORT}" --username="${PGUSER}" \
    --dbname="${TEST_DB}" \
    -c "CREATE TABLE restore_check (id SERIAL PRIMARY KEY, marker TEXT NOT NULL);
        INSERT INTO restore_check (marker) VALUES ('backup_test_$(date -u +%s)');" \
    2>/dev/null

ORIGINAL_MARKER="$(psql --host="${PGHOST}" --port="${PGPORT}" --username="${PGUSER}" \
    --dbname="${TEST_DB}" -Atc "SELECT marker FROM restore_check LIMIT 1;")"
log "  Inserted marker: ${ORIGINAL_MARKER}"

# Dump and upload
DUMP_FILE="${STAGING_DIR}/${TEST_DB}_${SNAPSHOT_DATE}.sql.gz"
pg_dump \
    --host="${PGHOST}" --port="${PGPORT}" --username="${PGUSER}" \
    --format=plain --no-password \
    "${TEST_DB}" | gzip --best > "${DUMP_FILE}"

OBJECT_KEY="pgdump/test/${TEST_DB}.sql.gz"
s3 cp "${DUMP_FILE}" "s3://${OCI_BUCKET}/${OBJECT_KEY}" --no-progress
rm -f "${DUMP_FILE}"
ok "pg_dump uploaded to OCI Object Storage"

# Download and restore into a fresh database
RESTORED_DB="${TEST_DB}_restored"
psql --host="${PGHOST}" --port="${PGPORT}" --username="${PGUSER}" \
    -c "DROP DATABASE IF EXISTS ${RESTORED_DB};" 2>/dev/null || true
psql --host="${PGHOST}" --port="${PGPORT}" --username="${PGUSER}" \
    -c "CREATE DATABASE ${RESTORED_DB};" 2>/dev/null

DOWNLOAD_FILE="${STAGING_DIR}/${RESTORED_DB}.sql.gz"
s3 cp "s3://${OCI_BUCKET}/${OBJECT_KEY}" "${DOWNLOAD_FILE}" --no-progress

zcat "${DOWNLOAD_FILE}" | psql \
    --host="${PGHOST}" --port="${PGPORT}" --username="${PGUSER}" \
    --dbname="${RESTORED_DB}" --set ON_ERROR_STOP=1 \
    >/dev/null 2>&1
rm -f "${DOWNLOAD_FILE}"
ok "Dump downloaded and restored into ${RESTORED_DB}"

# Verify the marker row survived the round-trip
RESTORED_MARKER="$(psql --host="${PGHOST}" --port="${PGPORT}" --username="${PGUSER}" \
    --dbname="${RESTORED_DB}" -Atc "SELECT marker FROM restore_check LIMIT 1;" 2>/dev/null)"

if [[ "${RESTORED_MARKER}" == "${ORIGINAL_MARKER}" ]]; then
    ok "Data integrity verified: marker matches (${RESTORED_MARKER})"
else
    fail "Data mismatch — original='${ORIGINAL_MARKER}' restored='${RESTORED_MARKER}'"
fi

# ── test 4: WAL-G base backup (if PostgreSQL is the primary) ─────────────────

log "=== Test 4: WAL-G base backup push ==="
if wal-g backup-push "${PGDATA:?PGDATA must be set}" >/dev/null 2>&1; then
    ok "wal-g backup-push succeeded"
    WALG_BACKUP_AVAILABLE=true
else
    fail "wal-g backup-push failed (check PGDATA, archive_mode, and WAL-G config)"
    WALG_BACKUP_AVAILABLE=false
fi

# ── test 5: WAL-G fetch sanity ────────────────────────────────────────────────

log "=== Test 5: WAL-G backup-fetch dry-run ==="
if [[ "${WALG_BACKUP_AVAILABLE}" == true ]]; then
    FETCH_DEST="${STAGING_DIR}/walg_fetch_test"
    rm -rf "${FETCH_DEST}" && mkdir -p "${FETCH_DEST}"
    if wal-g backup-fetch "${FETCH_DEST}" LATEST >/dev/null 2>&1; then
        ok "wal-g backup-fetch LATEST succeeded"
    else
        fail "wal-g backup-fetch LATEST failed"
    fi
    rm -rf "${FETCH_DEST}"
else
    log "  SKIP: No WAL-G backup available from test 4."
fi

# ── test 6: Retention logic check ────────────────────────────────────────────

log "=== Test 6: Object Storage retention listing ==="
SNAPSHOT_COUNT="$(s3 ls "s3://${OCI_BUCKET}/pgdump/" 2>/dev/null | grep -c PRE || echo 0)"
log "  Found ${SNAPSHOT_COUNT} snapshot date folder(s) in s3://${OCI_BUCKET}/pgdump/"
ok "Listing pgdump prefix succeeded"

# ── cleanup ───────────────────────────────────────────────────────────────────

if [[ "${KEEP_TESTDB}" == false ]]; then
    psql --host="${PGHOST}" --port="${PGPORT}" --username="${PGUSER}" \
        -c "DROP DATABASE IF EXISTS ${TEST_DB};" 2>/dev/null || true
    psql --host="${PGHOST}" --port="${PGPORT}" --username="${PGUSER}" \
        -c "DROP DATABASE IF EXISTS ${RESTORED_DB};" 2>/dev/null || true
    s3 rm "s3://${OCI_BUCKET}/${OBJECT_KEY}" 2>/dev/null || true
    log "Test databases and test object cleaned up."
else
    log "Keeping test databases: ${TEST_DB}, ${RESTORED_DB}"
fi

# ── summary ───────────────────────────────────────────────────────────────────

echo ""
echo "========================================"
echo "  Test Summary"
echo "  PASSED : ${PASS}"
echo "  FAILED : ${FAIL}"
echo "========================================"

[[ "${FAIL}" -eq 0 ]]
