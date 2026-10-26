#!/usr/bin/env bash
# One-shot, portfolio-only release. Run on the VPS; never touches host Nginx/DNS.
set -Eeuo pipefail
umask 077
ROOT=/opt/carlosandre-portfolio
BRANCH=codex/avallow-production
EXPECTED_COMMIT=${EXPECTED_COMMIT:-__RELEASE_COMMIT__}
[[ "$EXPECTED_COMMIT" =~ ^[a-f0-9]{40}$ ]] || { echo 'Use the delivery script pinned to its full commit.' >&2; exit 1; }
cd "$ROOT"
[[ "$(pwd -P)" == "$ROOT" ]]
for tool in docker git flock curl python3 awk; do command -v "$tool" >/dev/null; done
exec 9>/tmp/carlosandre-portfolio-prod.lock
flock -n 9 || { echo 'Another portfolio operation is running.' >&2; exit 1; }
[[ -z "$(git status --porcelain)" ]] || { echo 'Uncommitted server files: stop and review, do not discard.' >&2; exit 1; }
[[ -f .env.production ]]
docker buildx version >/dev/null
[[ $(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo) -ge 1536 ]] || { echo 'Need 1536 MiB available for bounded builds; existing apps were not stopped.' >&2; exit 1; }
[[ $(df -Pm . | awk 'NR==2{print $4}') -ge 6144 ]] || { echo 'Need 6 GiB free for local image builds.' >&2; exit 1; }
STAMP=$(date -u +%Y%m%dT%H%M%SZ)-$$
DIR="$ROOT/.private/releases/$STAMP"
mkdir -p "$DIR"
ACTIVE="$ROOT/.private/compose.portfolio-release.yml"
BASE=(-p carlosandre-portfolio-prod --env-file "$ROOT/.env.production" -f "$ROOT/docker-compose.prod.yml")
if [[ -f "$ROOT/.private/compose.avallow.yml" ]]; then BASE+=(-f "$ROOT/.private/compose.avallow.yml"); fi
dc() { docker compose "${BASE[@]}" "$@"; }
live() { docker compose "${BASE[@]}" -f "$ACTIVE" "$@"; }
old() { docker compose "${BASE[@]}" -f "$DIR/rollback.yml" "$@"; }
if [[ -f "$ACTIVE" ]]; then CURRENT=(-f "$ACTIVE"); else CURRENT=(); fi
current() { dc "${CURRENT[@]}" "$@"; }
current config --quiet
bash scripts/production/preflight.sh
BEFORE=$(git rev-parse HEAD)
printf '%s\n' "$BEFORE" > "$DIR/commit-before.txt"
printf 'services:\n' > "$DIR/rollback.yml"
for service in backend frontend worker; do
    id=$(current ps -q "$service")
    [[ -n "$id" ]]
    [[ $(docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' "$id") == carlosandre-portfolio-prod ]]
    image=$(docker inspect -f '{{.Image}}' "$id")
    tag="carlosandre-portfolio-rollback-$service:$STAMP"
    docker tag "$image" "$tag"
    printf '  %s:\n    image: %s\n' "$service" "$tag" >> "$DIR/rollback.yml"
done
for service in db nginx; do
    id=$(current ps -q "$service"); [[ -n "$id" ]]
    printf '%s\n' "$id" > "$DIR/$service-before.txt"
done
CHANGED=0
BUILDER="portfolio-build-$STAMP"
BUILDER_CREATED=0
cleanup() {
    result=$?
    trap - EXIT
    if [[ $result -ne 0 && $CHANGED -eq 1 ]]; then
        echo 'Release verification failed: restoring only portfolio app images.' >&2
        set +e
        # First revert only this release's target edit, refusing concurrent edits.
        if [[ -f "$DIR/cms-before.json" ]]; then
            old run --rm --no-deps -T -v "$ROOT/scripts/production/portfolio-release.py:/tmp/portfolio-release.py:ro" backend python /tmp/portfolio-release.py rollback "$STAMP" < "$DIR/cms-before.json" > "$DIR/data-rollback.log" 2>&1
            [[ $? -eq 0 ]] || echo 'Data rollback refused/failed: see private data-rollback.log; do not restore the database wholesale.' >&2
        fi
        cp "$DIR/rollback.yml" "$ACTIVE"
        old up -d --no-deps --no-build --wait --wait-timeout 180 backend frontend worker
        echo "Recovery files: $DIR" >&2
    fi
    if [[ $BUILDER_CREATED -eq 1 ]]; then docker buildx rm "$BUILDER" >/dev/null 2>&1 || true; fi
    if [[ $result -ne 0 ]]; then echo 'NOT VERIFIED. Preserve logs; no global Docker cleanup or DB restore.' >&2; fi
    exit "$result"
}
trap cleanup EXIT
export GIT_TERMINAL_PROMPT=0
git fetch origin "$BRANCH"
git cat-file -e "$EXPECTED_COMMIT^{commit}"
git merge-base --is-ancestor "$EXPECTED_COMMIT" "origin/$BRANCH"
git merge-base --is-ancestor "$BEFORE" "$EXPECTED_COMMIT" || { echo 'Production contains other commits; integrate them before deploying.' >&2; exit 1; }
git switch --detach "$EXPECTED_COMMIT"
printf '%s  %s\n' a1436552052ea70e34bd4f4da68d0c803eca93473fdae0d5c9077807e046b55a frontend/public/images/avallow-fintech.png | sha256sum -c -
# Dedicated bounded builder; never select it as the global/default builder.
docker buildx create --name "$BUILDER" --driver docker-container --driver-opt memory=1024m,cpu-period=100000,cpu-quota=75000 >/dev/null
BUILDER_CREATED=1
TAG="portfolio-${EXPECTED_COMMIT:0:12}"
BACKEND_IMAGE="carlosandre-portfolio-backend:$TAG"
FRONTEND_IMAGE="carlosandre-portfolio-frontend:$TAG"
docker buildx build --builder "$BUILDER" --load -f backend/Dockerfile.prod -t "$BACKEND_IMAGE" backend
docker buildx build --builder "$BUILDER" --load -t "$FRONTEND_IMAGE" frontend
# Small private snapshot + CMS revisions, not another full database/media backup.
backend=$(current ps -q backend)
docker cp scripts/production/portfolio-release.py "$backend:/tmp/portfolio-release.py" >/dev/null
docker exec "$backend" python /tmp/portfolio-release.py snapshot "$STAMP" > "$DIR/cms-before.json"
(cd "$DIR" && sha256sum cms-before.json > SHA256SUMS && sha256sum -c SHA256SUMS)
printf 'services:\n  backend:\n    image: %s\n  frontend:\n    image: %s\n  worker:\n    image: %s\n' "$BACKEND_IMAGE" "$FRONTEND_IMAGE" "$BACKEND_IMAGE" > "$DIR/new.yml"
CHANGED=1
cp "$DIR/new.yml" "$ACTIVE"
live stop --timeout 30 worker backend
# --no-deps: never run migrate or recreate DB, volumes, or either Nginx.
live up -d --no-deps --no-build --wait --wait-timeout 180 backend
live up -d --no-deps --no-build --wait --wait-timeout 180 frontend
backend=$(live ps -q backend)
docker cp scripts/production/portfolio-release.py "$backend:/tmp/portfolio-release.py" >/dev/null
docker exec -i "$backend" python /tmp/portfolio-release.py apply "$STAMP" < "$DIR/cms-before.json" > "$DIR/avallow-result.json"
curl --fail --silent --show-error --retry 8 --retry-delay 3 --retry-all-errors -H 'Host: carlosandre.tech' http://127.0.0.1:8088/api/health/ready -o /dev/null
# Through actual public HTTPS: session/CSRF enforced, staging upload only, cancelled.
docker exec "$backend" python /tmp/portfolio-release.py probe https://carlosandre.tech > "$DIR/public-verification.log" 2>&1
docker exec -i "$backend" python /tmp/portfolio-release.py verify "$STAMP" < "$DIR/cms-before.json"
live up -d --no-deps --no-build --wait --wait-timeout 180 worker
for service in db nginx; do [[ $(current ps -q "$service") == "$(cat "$DIR/$service-before.txt")" ]]; done
CHANGED=0
cat "$DIR/public-verification.log"
printf '\nVERIFIED: AVALLOW + DOCX on https://carlosandre.tech\nCommit: %s\nPrivate receipt: %s\n' "$EXPECTED_COMMIT" "$DIR"
