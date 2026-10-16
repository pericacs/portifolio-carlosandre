#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
backup() {
  local destination="backups/$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"
  mkdir -p "$destination"
  compose stop nginx worker frontend backend
  trap 'compose start backend frontend worker nginx' EXIT
  compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$destination/database.dump"
  compose run --rm --no-deps -T backend tar -C /app/uploads -czf - . > "$destination/media.tar.gz"
  git rev-parse HEAD > "$destination/revision.txt"
  compose config --images > "$destination/images.txt"
  for service in backend frontend worker db nginx; do
    container="$(compose ps -aq "$service")"
    if [[ -n "$container" ]]; then
      docker inspect --format '{{.Name}} {{.Config.Image}} {{.Image}}' "$container" >> "$destination/running-images.txt"
    fi
  done
  (cd "$destination" && sha256sum database.dump media.tar.gz > SHA256SUMS)
  compose start backend frontend worker nginx
  trap - EXIT
  echo "Backup: $destination"
}
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then backup; fi
