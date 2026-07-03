#!/usr/bin/env bash
# Install the LexBangla DB backup suite on an OCI Compute instance.
# Run as root (or with sudo) on the target server.
#
# What this does:
#   1. Installs WAL-G binary (latest stable release)
#   2. Installs aws-cli v2 (used for pg_dump OCI Object Storage uploads)
#   3. Copies scripts to /usr/local/lib/lexbangla-backup/
#   4. Creates /usr/local/bin/lexbangla-db-backup wrapper symlink
#   5. Installs systemd service + timer
#   6. Creates /etc/lexbangla/ config directory with example config
#   7. Configures PostgreSQL archive_command for continuous WAL shipping
#   8. Enables and starts the systemd timer

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log()  { echo "[INSTALL] $*"; }
fail() { echo "[INSTALL] ERROR: $*" >&2; exit 1; }

[[ "$(id -u)" -eq 0 ]] || fail "Must run as root."

# ── 1. Install WAL-G ──────────────────────────────────────────────────────────

install_walg() {
    if command -v wal-g >/dev/null 2>&1; then
        log "wal-g already installed: $(wal-g --version)"
        return
    fi

    log "Installing WAL-G..."
    local arch
    arch="$(uname -m)"
    local walg_arch="amd64"
    [[ "${arch}" == "aarch64" ]] && walg_arch="arm64"

    # Use GitHub releases — pin to a known-good version or set WALG_VERSION env
    local version="${WALG_VERSION:-v3.0.3}"
    local url="https://github.com/wal-g/wal-g/releases/download/${version}/wal-g-pg-ubuntu-20.04-${walg_arch}.tar.gz"

    log "Downloading ${url}..."
    curl -fsSL "${url}" | tar -xz -C /tmp
    install -m 0755 /tmp/wal-g /usr/local/bin/wal-g
    rm -f /tmp/wal-g
    log "WAL-G installed: $(wal-g --version)"
}

# ── 2. Install aws-cli v2 ─────────────────────────────────────────────────────

install_awscli() {
    if command -v aws >/dev/null 2>&1; then
        log "aws cli already installed: $(aws --version)"
        return
    fi

    log "Installing AWS CLI v2..."
    local arch
    arch="$(uname -m)"
    local awscli_arch="x86_64"
    [[ "${arch}" == "aarch64" ]] && awscli_arch="aarch64"

    curl -fsSL \
        "https://awscli.amazonaws.com/awscli-exe-linux-${awscli_arch}.zip" \
        -o /tmp/awscliv2.zip
    unzip -q /tmp/awscliv2.zip -d /tmp/awscliv2_install
    /tmp/awscliv2_install/aws/install --update
    rm -rf /tmp/awscliv2.zip /tmp/awscliv2_install
    log "AWS CLI installed: $(aws --version)"
}

# ── 3. Copy scripts ───────────────────────────────────────────────────────────

install_scripts() {
    local dest="/usr/local/lib/lexbangla-backup"
    log "Installing scripts to ${dest}..."
    mkdir -p "${dest}"
    install -m 0750 "${SCRIPT_DIR}/walg-backup.sh"    "${dest}/walg-backup.sh"
    install -m 0750 "${SCRIPT_DIR}/pgdump-snapshot.sh" "${dest}/pgdump-snapshot.sh"
    install -m 0750 "${SCRIPT_DIR}/restore.sh"         "${dest}/restore.sh"
    install -m 0750 "${SCRIPT_DIR}/backup-wrapper.sh"  "${dest}/backup-wrapper.sh"
    chown -R postgres:postgres "${dest}"

    ln -sf "${dest}/backup-wrapper.sh" /usr/local/bin/lexbangla-db-backup
    ln -sf "${dest}/restore.sh"        /usr/local/bin/lexbangla-db-restore
    log "Scripts installed."
}

# ── 4. Config directory ───────────────────────────────────────────────────────

install_config() {
    local config_dir="/etc/lexbangla"
    local config_file="${config_dir}/db-backup.env"
    local example_file="${config_dir}/db-backup.env.example"

    mkdir -p "${config_dir}"
    install -m 0640 -o postgres -g postgres \
        "${SCRIPT_DIR}/config.env.example" "${example_file}"

    if [[ ! -f "${config_file}" ]]; then
        log "Creating empty config at ${config_file}."
        log "  !! EDIT IT before the timer fires. !!"
        install -m 0600 -o postgres -g postgres \
            "${SCRIPT_DIR}/config.env.example" "${config_file}"
    else
        log "Config file already exists: ${config_file} — not overwritten."
    fi

    mkdir -p /var/tmp/lexbangla-backup /var/log/lexbangla
    chown postgres:postgres /var/tmp/lexbangla-backup /var/log/lexbangla
}

# ── 5. systemd units ──────────────────────────────────────────────────────────

install_systemd() {
    log "Installing systemd units..."
    install -m 0644 \
        "${SCRIPT_DIR}/systemd/lexbangla-db-backup.service" \
        /etc/systemd/system/lexbangla-db-backup.service
    install -m 0644 \
        "${SCRIPT_DIR}/systemd/lexbangla-db-backup.timer" \
        /etc/systemd/system/lexbangla-db-backup.timer

    systemctl daemon-reload
    systemctl enable --now lexbangla-db-backup.timer
    log "Timer status:"
    systemctl status lexbangla-db-backup.timer --no-pager || true
}

# ── 6. PostgreSQL archive_command ─────────────────────────────────────────────

configure_postgres_archiving() {
    local pgdata="${PGDATA:-}"
    if [[ -z "${pgdata}" ]]; then
        log "PGDATA not set — skipping automatic postgresql.conf update."
        log "  Manually add these lines to postgresql.conf:"
        echo ""
        echo "    wal_level = replica"
        echo "    archive_mode = on"
        echo "    archive_command = '/usr/local/lib/lexbangla-backup/walg-backup.sh wal %p'"
        echo "    archive_timeout = 300"
        echo ""
        return
    fi

    local conf="${pgdata}/postgresql.conf"
    [[ -f "${conf}" ]] || fail "postgresql.conf not found at ${conf}"

    log "Updating ${conf} for WAL archiving..."

    # Idempotent: only add if not already set
    for param in \
        "wal_level = replica" \
        "archive_mode = on" \
        "archive_command = '/usr/local/lib/lexbangla-backup/walg-backup.sh wal %p'" \
        "archive_timeout = 300"
    do
        local key="${param%%=*}"
        key="${key%% }"
        if grep -qE "^#?${key}\s*=" "${conf}"; then
            # Comment out the old line and append the new value
            sed -i "s|^#\?${key}\s*=.*|# & (overridden by lexbangla installer)|" "${conf}"
        fi
        echo "${param}" >> "${conf}"
    done

    log "postgresql.conf updated. Reload or restart PostgreSQL to apply:"
    log "  systemctl reload postgresql  (if already running with archive_mode=off, restart instead)"
}

# ── main ──────────────────────────────────────────────────────────────────────

log "=== LexBangla DB Backup Installer ==="
install_walg
install_awscli
install_scripts
install_config
install_systemd
configure_postgres_archiving

log ""
log "=== Installation complete ==="
log ""
log "Next steps:"
log "  1. Edit /etc/lexbangla/db-backup.env with your OCI credentials."
log "  2. Verify: sudo -u postgres /usr/local/bin/lexbangla-db-backup"
log "  3. Check the timer: systemctl list-timers lexbangla-db-backup.timer"
log "  4. View logs: journalctl -u lexbangla-db-backup -f"
log ""
log "Restore:"
log "  sudo -u postgres lexbangla-db-restore list"
log "  sudo -u postgres lexbangla-db-restore pgdump --date YYYY-MM-DD"
log "  sudo -u postgres lexbangla-db-restore walg   [--target-time '...']"
