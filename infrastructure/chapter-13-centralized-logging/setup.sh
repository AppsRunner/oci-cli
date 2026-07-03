#!/usr/bin/env bash
# Chapter 13 — Centralized Logging setup script for LexBangla on OCI.
# Run as the deploy user on the OCI compute instance.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Preflight ─────────────────────────────────────────────────────────────────
command -v docker        >/dev/null 2>&1 || { echo "ERROR: docker not found"; exit 1; }
command -v docker-compose >/dev/null 2>&1 \
  || docker compose version >/dev/null 2>&1 \
  || { echo "ERROR: docker compose not found"; exit 1; }

if [[ ! -f "$SCRIPT_DIR/.env" ]]; then
  echo "ERROR: .env file not found. Copy .env.example and set values."
  exit 1
fi

# ── Host log directories ──────────────────────────────────────────────────────
echo "Creating host log directories..."
sudo mkdir -p /var/log/nginx /var/log/django /var/log/gunicorn
sudo chmod 755 /var/log/nginx /var/log/django /var/log/gunicorn

# Promtail runs as root inside the container so it can read the Docker socket.
# Loki data volume is owned by UID 10001.
echo "Setting volume permissions for Loki..."
sudo chown -R 10001:10001 "$(docker volume inspect loki_data --format '{{.Mountpoint}}' 2>/dev/null || echo '/var/lib/docker/volumes/loki_data/_data')" 2>/dev/null || true

# ── Ensure shared network exists ─────────────────────────────────────────────
if ! docker network inspect lexbangla_net >/dev/null 2>&1; then
  echo "Creating external network lexbangla_net..."
  docker network create lexbangla_net
fi

# ── Nginx logging config ──────────────────────────────────────────────────────
echo "Deploying Nginx logging config..."
sudo cp "$SCRIPT_DIR/nginx/logging.conf" /etc/nginx/conf.d/logging.conf
sudo nginx -t && sudo systemctl reload nginx || echo "WARN: Nginx reload failed — check nginx -t output above."

# ── Start the logging stack ───────────────────────────────────────────────────
echo "Starting Loki + Promtail + Grafana..."
cd "$SCRIPT_DIR"

COMPOSE_CMD="docker compose"
if command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
fi

$COMPOSE_CMD -f docker-compose.logging.yml --env-file .env pull
$COMPOSE_CMD -f docker-compose.logging.yml --env-file .env up -d

echo ""
echo "✓ Logging stack started."
echo "  Loki:    http://$(hostname -I | awk '{print $1}'):3100/ready"
echo "  Grafana: http://$(hostname -I | awk '{print $1}'):3000"
echo ""
echo "Open Grafana and navigate to Dashboards → LexBangla → LexBangla — Centralized Logs"
