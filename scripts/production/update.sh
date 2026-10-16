#!/usr/bin/env bash
source "$(dirname "$0")/backup.sh"
compose config --quiet
compose build --pull
backup
# Quiesce writers until migrations complete; on failure keep them stopped for diagnosis.
compose stop nginx worker frontend backend
compose run --rm migrate
compose up -d --wait --wait-timeout 180 backend frontend worker nginx
curl --fail --silent --show-error https://carlosandre.tech/api/health/ready
