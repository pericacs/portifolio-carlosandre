#!/usr/bin/env bash
source "$(dirname "$0")/backup.sh"
compose config --quiet
bash scripts/production/preflight.sh
compose build --pull
backup
# Quiesce writers until migrations complete; on failure keep them stopped for diagnosis.
compose stop nginx worker frontend backend
compose run --rm migrate
compose up -d --wait --wait-timeout 180 backend frontend worker nginx
curl --fail --silent --show-error -H 'Host: carlosandre.tech' http://127.0.0.1:8088/api/health/ready
