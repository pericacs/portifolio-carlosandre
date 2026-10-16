#!/usr/bin/env bash
# Read-only against the backup; restores only to disposable named volumes.
set -Eeuo pipefail
cd "$(dirname "$0")/../.."
directory="$(realpath "${1:?Usage: restore-drill.sh backup-directory}")"
(cd "$directory" && sha256sum -c SHA256SUMS)
id="carlosandre-drill-$(date +%s)-$$"
cleanup() { docker rm -f "$id" >/dev/null 2>&1 || true; docker volume rm "$id-db" "$id-media" >/dev/null 2>&1 || true; }
trap cleanup EXIT
password="$(openssl rand -hex 24)"
docker volume create "$id-db" >/dev/null
docker volume create "$id-media" >/dev/null
docker run -d --name "$id" --network none -e POSTGRES_PASSWORD="$password" -v "$id-db:/var/lib/postgresql/data" postgres:16-alpine >/dev/null
for attempt in $(seq 1 60); do
  if docker exec "$id" pg_isready -U postgres >/dev/null 2>&1; then break; fi
  sleep 1
done
docker exec -i "$id" pg_restore -U postgres -d postgres --no-owner --no-privileges --exit-on-error --single-transaction < "$directory/database.dump"
docker exec "$id" psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c 'SELECT version_num FROM alembic_version'
docker run --rm -i --network none -v "$id-media:/restore" alpine:3.22 tar -C /restore -xzf - < "$directory/media.tar.gz"
docker run --rm --network none -v "$id-media:/restore:ro" alpine:3.22 sh -c 'find /restore -type f | wc -l'
echo 'Restore drill passed. Compare business row counts and media with backup inventory before accepting RTO/RPO.'
