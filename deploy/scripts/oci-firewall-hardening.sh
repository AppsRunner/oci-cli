#!/bin/bash
# OCI instance firewall hardening for LexBangla production.
#
# Applies two layers:
#   1. OS-level firewall via ufw (runs on the instance itself)
#   2. OCI Security List rules via oci-cli (controls VCN-level ingress)
#
# Prerequisites:
#   - Run as root (sudo) on the OCI compute instance
#   - OCI CLI configured: ~/.oci/config with a valid profile
#   - jq installed
#   - Environment variables SUBNET_OCID and OCI_PROFILE set (or defaults used)
#
# Usage:
#   sudo SUBNET_OCID=ocid1.subnet.oc1... OCI_PROFILE=DEFAULT ./oci-firewall-hardening.sh

set -euo pipefail

OCI_PROFILE="${OCI_PROFILE:-DEFAULT}"
ADMIN_CIDR="${ADMIN_CIDR:-0.0.0.0/0}"   # Restrict SSH to your office CIDR in production

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

### ─── 1. OS-LEVEL FIREWALL (ufw) ──────────────────────────────────────────────

log "==> Configuring ufw OS firewall..."

if ! command -v ufw &>/dev/null; then
  apt-get update -qq && apt-get install -y ufw
fi

# Reset to defaults (non-interactive)
ufw --force reset

# Default deny incoming, allow outgoing
ufw default deny incoming
ufw default allow outgoing

# SSH — restrict to admin CIDR
ufw allow from "$ADMIN_CIDR" to any port 22 proto tcp comment "SSH admin access"

# HTTP / HTTPS — public
ufw allow 80/tcp  comment "HTTP (ACME + redirect)"
ufw allow 443/tcp comment "HTTPS"

# Block all OCI internal metadata service from containers
# (Docker has its own bridge network; block it at host level as defence-in-depth)
ufw deny out from any to 169.254.169.254 comment "Block IMDS from containers"

# Enable (non-interactive)
ufw --force enable

log "ufw status:"
ufw status verbose

### ─── 2. SYSTEM HARDENING ──────────────────────────────────────────────────────

log "==> Applying sysctl hardening..."

cat > /etc/sysctl.d/99-lexbangla-hardening.conf << 'EOF'
# IP spoofing protection
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Ignore ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0

# Ignore ping broadcasts
net.ipv4.icmp_echo_ignore_broadcasts = 1

# Log martian packets
net.ipv4.conf.all.log_martians = 1

# Disable IPv6 if not used
net.ipv6.conf.all.disable_ipv6 = 0

# SYN flood protection
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 2
net.ipv4.tcp_syn_retries = 5

# Increase connection limits for Nginx
net.core.somaxconn = 65535
net.ipv4.ip_local_port_range = 1024 65535
EOF

sysctl -p /etc/sysctl.d/99-lexbangla-hardening.conf

### ─── 3. SSH HARDENING ──────────────────────────────────────────────────────────

log "==> Hardening SSH configuration..."

SSHD_CONF="/etc/ssh/sshd_config.d/99-lexbangla.conf"
cat > "$SSHD_CONF" << 'EOF'
# LexBangla production SSH hardening
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
X11Forwarding no
AllowTcpForwarding no
ClientAliveInterval 300
ClientAliveCountMax 2
MaxAuthTries 3
MaxSessions 10
EOF

sshd -t && systemctl reload sshd
log "SSH hardening applied."

### ─── 4. OCI SECURITY LIST (VCN-level) ────────────────────────────────────────

if [[ -z "${SUBNET_OCID:-}" ]]; then
  log "WARN: SUBNET_OCID not set — skipping OCI Security List update."
  log "      Set SUBNET_OCID=ocid1.subnet.oc1... and re-run to apply VCN rules."
else
  log "==> Fetching current Security List for subnet $SUBNET_OCID..."

  SECURITY_LIST_OCID=$(oci --profile "$OCI_PROFILE" network subnet get \
    --subnet-id "$SUBNET_OCID" \
    --query "data.\"security-list-ids\"[0]" \
    --raw-output)

  log "Security List OCID: $SECURITY_LIST_OCID"

  # Build desired ingress rules as JSON
  INGRESS_RULES=$(cat << 'RULES'
[
  {
    "source": "0.0.0.0/0",
    "protocol": "6",
    "isStateless": false,
    "description": "HTTPS public access",
    "tcpOptions": { "destinationPortRange": { "min": 443, "max": 443 } }
  },
  {
    "source": "0.0.0.0/0",
    "protocol": "6",
    "isStateless": false,
    "description": "HTTP (ACME challenge + redirect)",
    "tcpOptions": { "destinationPortRange": { "min": 80, "max": 80 } }
  },
  {
    "source": "ADMIN_CIDR_PLACEHOLDER",
    "protocol": "6",
    "isStateless": false,
    "description": "SSH admin access",
    "tcpOptions": { "destinationPortRange": { "min": 22, "max": 22 } }
  },
  {
    "source": "0.0.0.0/0",
    "protocol": "1",
    "isStateless": false,
    "description": "ICMP ping",
    "icmpOptions": { "type": 8 }
  }
]
RULES
)

  INGRESS_RULES="${INGRESS_RULES//ADMIN_CIDR_PLACEHOLDER/$ADMIN_CIDR}"

  log "==> Updating OCI Security List ingress rules..."
  oci --profile "$OCI_PROFILE" network security-list update \
    --security-list-id "$SECURITY_LIST_OCID" \
    --ingress-security-rules "$INGRESS_RULES" \
    --force

  log "OCI Security List updated."
fi

### ─── 5. FAIL2BAN ──────────────────────────────────────────────────────────────

log "==> Installing and configuring fail2ban..."

if ! command -v fail2ban-client &>/dev/null; then
  apt-get install -y fail2ban
fi

cat > /etc/fail2ban/jail.d/lexbangla.conf << 'EOF'
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 5
ignoreip = 127.0.0.1/8

[sshd]
enabled  = true
port     = ssh
logpath  = %(sshd_log)s
maxretry = 3

[nginx-http-auth]
enabled  = true
port     = http,https
logpath  = /var/log/nginx/error.log

[nginx-limit-req]
enabled  = true
port     = http,https
logpath  = /var/log/nginx/error.log
maxretry = 10
EOF

systemctl enable fail2ban && systemctl restart fail2ban
log "fail2ban configured."

log "==> Firewall hardening complete."
log "    Review: ufw status verbose"
log "    Review: fail2ban-client status"
