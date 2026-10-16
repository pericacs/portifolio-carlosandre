#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
[[ "${1:-}" == "--first-install" ]] || { echo 'Use update.sh for existing installations; first deploy requires --first-install' >&2; exit 1; }
compose config --quiet
compose build --pull
compose up -d db
compose run --rm migrate
compose up -d --wait --wait-timeout 180 backend frontend worker nginx
curl --fail --silent --show-error https://carlosandre.tech/api/health/ready
