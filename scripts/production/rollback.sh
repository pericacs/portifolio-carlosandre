#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
tag="${1:?Usage: rollback.sh previous-image-tag}"
export RELEASE_TAG="$tag"
docker image inspect "carlosandre-backend:$tag" "carlosandre-frontend:$tag" >/dev/null
# Only compatible application rollback. Never downgrade the schema automatically.
compose up -d --no-build --no-deps --wait --wait-timeout 180 backend frontend worker nginx
