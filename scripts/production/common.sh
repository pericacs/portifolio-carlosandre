#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
ENV_FILE="${ENV_FILE:-.env.production}"
[[ -f "$ENV_FILE" ]] || { echo 'Missing production env file' >&2; exit 1; }
export ENV_FILE
compose() { docker compose -p carlosandre-portfolio-prod --env-file "$ENV_FILE" -f docker-compose.prod.yml "$@"; }
# Serialize all operations, including backup/restore.
exec 9>/tmp/carlosandre-portfolio-prod.lock
flock -n 9 || { echo 'Another production operation is running' >&2; exit 1; }
umask 077
