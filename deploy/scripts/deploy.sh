#!/bin/bash
# LexBangla production deploy script.
# Called by the systemd lexbangla-deploy.service and the GitHub Actions CD pipeline.
#
# Usage: ./deploy.sh [IMAGE_TAG]
#   IMAGE_TAG defaults to "latest"

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_TAG="${1:-latest}"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.prod.yml"
LOG_FILE="/var/log/lexbangla/deploy.log"
ROLLBACK_TAG_FILE="/var/run/lexbangla-previous-tag"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

mkdir -p /var/log/lexbangla

log "==> Starting deployment (tag: $IMAGE_TAG)"

if [[ ! -f "$DEPLOY_DIR/.env.prod" ]]; then
  log "ERROR: $DEPLOY_DIR/.env.prod not found."
  exit 1
fi

source "$DEPLOY_DIR/.env.prod"

cd "$DEPLOY_DIR"

# Save current image tag for rollback
if docker inspect "lexbangla_backend" &>/dev/null 2>&1; then
  CURRENT_TAG=$(docker inspect --format='{{index .Config.Image}}' lexbangla_backend 2>/dev/null | awk -F: '{print $2}' || echo "unknown")
  echo "$CURRENT_TAG" > "$ROLLBACK_TAG_FILE"
  log "Current tag saved for rollback: $CURRENT_TAG"
fi

# Pull new images
log "==> Pulling images (tag: $IMAGE_TAG)..."
IMAGE_TAG="$IMAGE_TAG" docker compose -f "$COMPOSE_FILE" pull backend frontend

# Run Django migrations
log "==> Running database migrations..."
IMAGE_TAG="$IMAGE_TAG" docker compose -f "$COMPOSE_FILE" run --rm --no-deps backend \
  python manage.py migrate --no-input

# Collect static files
log "==> Collecting static files..."
IMAGE_TAG="$IMAGE_TAG" docker compose -f "$COMPOSE_FILE" run --rm --no-deps backend \
  python manage.py collectstatic --no-input --clear

# Rolling restart — bring up new containers before stopping old ones
log "==> Performing rolling restart..."
IMAGE_TAG="$IMAGE_TAG" docker compose -f "$COMPOSE_FILE" up -d \
  --no-deps \
  --remove-orphans \
  backend celery frontend

# Health check
log "==> Running health check..."
RETRIES=12
INTERVAL=5
for i in $(seq 1 $RETRIES); do
  if curl -fs "https://${DOMAIN}/api/health/" > /dev/null 2>&1; then
    log "==> Health check passed."
    break
  fi
  if [[ $i -eq $RETRIES ]]; then
    log "ERROR: Health check failed after $((RETRIES * INTERVAL))s — rolling back..."
    if [[ -f "$ROLLBACK_TAG_FILE" ]]; then
      PREV_TAG=$(cat "$ROLLBACK_TAG_FILE")
      log "==> Rolling back to $PREV_TAG..."
      IMAGE_TAG="$PREV_TAG" docker compose -f "$COMPOSE_FILE" up -d \
        --no-deps backend celery frontend
    fi
    exit 1
  fi
  log "    Attempt $i/$RETRIES — waiting ${INTERVAL}s..."
  sleep "$INTERVAL"
done

# Prune old images to free disk space
docker image prune -f --filter "until=24h" >> "$LOG_FILE" 2>&1 || true

log "==> Deployment complete (tag: $IMAGE_TAG)"
