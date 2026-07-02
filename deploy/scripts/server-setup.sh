#!/bin/bash
# One-time OCI instance bootstrap for LexBangla production.
# Run as root immediately after provisioning a fresh OCI Ubuntu 22.04 instance.
#
# Usage: sudo bash server-setup.sh

set -euo pipefail

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "==> Updating system packages..."
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq

log "==> Installing dependencies..."
apt-get install -y -qq \
  curl git jq ufw fail2ban \
  ca-certificates gnupg lsb-release

# Docker
log "==> Installing Docker..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update -qq
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable docker
systemctl start docker

# OCI CLI
log "==> Installing OCI CLI..."
bash -c "$(curl -fsSL https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)" \
  -- --accept-all-defaults

# Create deploy user
log "==> Creating deploy user..."
id -u deploy &>/dev/null || useradd -m -s /bin/bash -G docker,sudo deploy
mkdir -p /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/authorized_keys 2>/dev/null || true
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys 2>/dev/null || true

# Deployment directory
log "==> Creating /opt/lexbangla..."
mkdir -p /opt/lexbangla/deploy
chown -R deploy:deploy /opt/lexbangla

# Install systemd units
log "==> Installing systemd units..."
UNIT_SRC="/opt/lexbangla/deploy/systemd"
if [[ -d "$UNIT_SRC" ]]; then
  cp "$UNIT_SRC/"*.service /etc/systemd/system/
  cp "$UNIT_SRC/"*.timer   /etc/systemd/system/ 2>/dev/null || true
  systemctl daemon-reload
  systemctl enable lexbangla.service
  systemctl enable lexbangla-certbot.timer 2>/dev/null || true
  log "systemd units installed."
else
  log "WARN: $UNIT_SRC not found — deploy the repo first, then re-run systemd unit installation."
fi

log "==> Server setup complete."
log ""
log "Next steps:"
log "  1. Copy deploy/ directory to /opt/lexbangla/deploy/"
log "  2. Create /opt/lexbangla/deploy/.env.prod (from .env.prod.example)"
log "  3. sudo ./deploy/certbot/init-letsencrypt.sh"
log "  4. sudo systemctl start lexbangla"
log "  5. sudo ./deploy/scripts/oci-firewall-hardening.sh"
