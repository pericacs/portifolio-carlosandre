#!/usr/bin/env bash
# Read-only checks, before any deployment/update. Never stops foreign services.
set -Eeuo pipefail
cd "$(dirname "$0")/../.."
[[ "$(pwd -P)" == /opt/carlosandre-portfolio ]] || { echo 'Expected /opt/carlosandre-portfolio; aborting.' >&2; exit 1; }
command -v ss >/dev/null || { echo 'Install iproute2 for port checking.' >&2; exit 1; }
docker info >/dev/null
owned="$(docker ps -q --filter label=com.docker.compose.project=carlosandre-portfolio-prod --filter label=com.docker.compose.service=nginx)"
for container in $(docker ps -q); do
    if docker port "$container" 2>/dev/null | grep -Eq ':(8088)$'; then
        if [[ "$container" != "$owned" ]]; then
            echo 'Port 8088 is published by another container; aborting.' >&2
            exit 1
        fi
    fi
done
listeners="$(ss -H -ltnp '( sport = :8088 )')"
if [[ -n "$owned" ]]; then
    [[ "$(docker port "$owned" 80/tcp)" == 127.0.0.1:8088 ]] || { echo 'Existing project has unexpected port mapping; aborting.' >&2; exit 1; }
fi
while IFS= read -r listener; do
    [[ -z "$listener" ]] && continue
    if [[ -z "$owned" || "$listener" != *docker-proxy* || "$listener" != *127.0.0.1:8088* ]]; then
        echo 'Port 8088 has an unverified host listener; aborting without changing it.' >&2
        exit 1
    fi
done <<< "$listeners"
echo 'Preflight passed: 8088 available or held by this project; no foreign service changed.'
