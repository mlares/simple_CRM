#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_TAG="${SIMPLE_CRM_PRODUCTION_IMAGE_TAG:-simple-crm:production-smoke}"
CONTAINER_NAME="simple-crm-production-smoke-$$"
SECRET_KEY="crm020-production-smoke-secret-key-with-enough-entropy-1234567890"

cleanup() {
  docker rm --force "$CONTAINER_NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

command -v docker >/dev/null || {
  echo "docker is required for the production image verifier" >&2
  exit 2
}
docker info >/dev/null

cd "$PROJECT_ROOT"
docker build --tag "$IMAGE_TAG" .
docker run --detach --name "$CONTAINER_NAME" --publish 127.0.0.1::8000 \
  --env DJANGO_SECRET_KEY="$SECRET_KEY" \
  --env DJANGO_ALLOWED_HOSTS=localhost \
  --env DATABASE_URL=postgresql://smoke:smoke@127.0.0.1:5432/smoke \
  --env DJANGO_DEBUG=false \
  --env DJANGO_SESSION_COOKIE_SECURE=true \
  --env DJANGO_CSRF_COOKIE_SECURE=true \
  --env DJANGO_TRUST_X_FORWARDED_PROTO=true \
  --env WEB_CONCURRENCY=1 \
  "$IMAGE_TAG" >/dev/null

PORT="$(docker port "$CONTAINER_NAME" 8000/tcp | sed -n '1s/.*://p')"
BASE_URL="http://127.0.0.1:${PORT}"
for _attempt in $(seq 1 30); do
  if curl --fail --silent --show-error --max-time 2 \
    --header 'Host: localhost' \
    --header 'X-Forwarded-Proto: https' \
    "${BASE_URL}/health/live/" >/dev/null; then
    break
  fi
  sleep 1
done
curl --fail --silent --show-error --max-time 5 \
  --header 'Host: localhost' \
  --header 'X-Forwarded-Proto: https' \
  "${BASE_URL}/health/live/" >/dev/null

PAGE="$(curl --fail --silent --show-error --max-time 5 \
  --header 'Host: localhost' \
  --header 'X-Forwarded-Proto: https' \
  "${BASE_URL}/")"
STATIC_PATH="$(printf '%s' "$PAGE" | sed -n 's/.*href="\([^"?]*bootstrap\.min\.[0-9a-f]\{12\}\.css\)".*/\1/p' | head -n 1)"
test -n "$STATIC_PATH" || {
  echo "rendered page did not contain a manifest-hashed Bootstrap asset" >&2
  exit 1
}
curl --fail --silent --show-error --max-time 5 \
  --header 'Host: localhost' \
  --header 'X-Forwarded-Proto: https' \
  "${BASE_URL}${STATIC_PATH}" >/dev/null

docker exec "$CONTAINER_NAME" test -w /tmp/simplecrm-runtime
docker exec "$CONTAINER_NAME" test -S /tmp/simplecrm-runtime/gunicorn.ctl
docker exec "$CONTAINER_NAME" test -f /app/staticfiles/staticfiles.json
echo "Production image rendered-page and hashed-static smoke passed"
