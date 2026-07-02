#!/bin/bash
# Bootstrap Let's Encrypt certificates for LexBangla.
# Run once on a fresh server before starting the full stack.
# Usage: sudo ./init-letsencrypt.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(dirname "$SCRIPT_DIR")"

if [[ ! -f "$DEPLOY_DIR/.env.prod" ]]; then
  echo "ERROR: $DEPLOY_DIR/.env.prod not found. Copy .env.prod.example and fill in values."
  exit 1
fi

source "$DEPLOY_DIR/.env.prod"

: "${DOMAIN:?DOMAIN must be set in .env.prod}"
: "${CERTBOT_EMAIL:?CERTBOT_EMAIL must be set in .env.prod}"

STAGING="${STAGING:-0}"  # Set STAGING=1 to test against Let's Encrypt staging CA

echo "==> Initialising Let's Encrypt for domain: $DOMAIN"
echo "    Staging mode: $STAGING"

# Create required directories
mkdir -p "$DEPLOY_DIR/certbot_data/certbot/certs"
mkdir -p "$DEPLOY_DIR/certbot_data/certbot/webroot"

# Create a temporary self-signed cert so Nginx can start on first boot
if [[ ! -f "$DEPLOY_DIR/certbot_data/certbot/certs/live/$DOMAIN/fullchain.pem" ]]; then
  echo "==> Creating temporary self-signed certificate..."
  mkdir -p "$DEPLOY_DIR/certbot_data/certbot/certs/live/$DOMAIN"
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout "$DEPLOY_DIR/certbot_data/certbot/certs/live/$DOMAIN/privkey.pem" \
    -out    "$DEPLOY_DIR/certbot_data/certbot/certs/live/$DOMAIN/fullchain.pem" \
    -subj   "/CN=$DOMAIN" 2>/dev/null
  # certbot needs chain.pem too
  cp "$DEPLOY_DIR/certbot_data/certbot/certs/live/$DOMAIN/fullchain.pem" \
     "$DEPLOY_DIR/certbot_data/certbot/certs/live/$DOMAIN/chain.pem"
fi

echo "==> Starting Nginx (HTTP only for ACME challenge)..."
cd "$DEPLOY_DIR"
docker compose -f docker-compose.prod.yml up -d nginx

echo "==> Waiting for Nginx to be ready..."
sleep 5

STAGING_ARG=""
if [[ "$STAGING" -eq 1 ]]; then
  STAGING_ARG="--staging"
fi

echo "==> Requesting Let's Encrypt certificate..."
docker compose -f docker-compose.prod.yml run --rm certbot certbot certonly \
  --webroot \
  --webroot-path /var/www/certbot \
  $STAGING_ARG \
  --email "$CERTBOT_EMAIL" \
  --agree-tos \
  --no-eff-email \
  --force-renewal \
  -d "$DOMAIN" \
  -d "www.$DOMAIN"

echo "==> Reloading Nginx with real certificate..."
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload

echo "==> Done. Certificate is live for $DOMAIN."
echo "    Renewal is handled automatically by the certbot container every 12 hours."
