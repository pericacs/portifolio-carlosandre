#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
directory="$(realpath "${1:?Usage: restore.sh backup-directory --confirm-replace-production}")"
[[ "${2:-}" == --confirm-replace-production ]] || { echo 'Explicit replacement flag required' >&2; exit 1; }
(cd "$directory" && sha256sum -c SHA256SUMS)
tar -tzf "$directory/media.tar.gz" >/dev/null
compose stop nginx worker frontend backend
compose up -d --wait db
compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --exit-on-error --single-transaction' < "$directory/database.dump"
compose run --rm --no-deps -T backend python -c 'from pathlib import Path; import shutil; p=Path("/app/uploads"); [(shutil.rmtree(x) if x.is_dir() else x.unlink()) for x in p.iterdir()]'
compose run --rm --no-deps -T backend tar -C /app/uploads -xzf - < "$directory/media.tar.gz"
# Start explicitly only after choosing the application revision compatible with this backup.
echo 'Restore complete; inspect revision.txt and images.txt, select matching checkout/tag, then start services.'
