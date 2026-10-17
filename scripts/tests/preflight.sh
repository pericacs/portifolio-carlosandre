#!/usr/bin/env bash
# Run in a disposable Linux container with scripts mounted in /opt/carlosandre-portfolio/scripts.
set -Eeuo pipefail
mock="$(mktemp -d)"
cat > "$mock/docker" <<'MOCK'
#!/usr/bin/env bash
case "$1" in
 info) exit 0 ;;
 ps)
   if [[ "$*" == *com.docker.compose.project* ]]; then
     [[ "$SCENARIO" != own && "$SCENARIO" != own_foreign_listener ]] || echo owned
   else
     case "$SCENARIO" in foreign) echo foreign;; own|own_foreign_listener) echo owned;; esac
   fi ;;
 port)
   if [[ "${3:-}" == 80/tcp ]]; then echo 127.0.0.1:8088
   else echo '80/tcp -> 127.0.0.1:8088'; fi ;;
 *) echo 'Unexpected docker command in read-only preflight' >&2; exit 99 ;;
esac
exit 0
MOCK
cat > "$mock/ss" <<'MOCK'
#!/usr/bin/env bash
case "$SCENARIO" in
 host|own_foreign_listener) echo 'LISTEN 0 511 127.0.0.1:8088 0.0.0.0:* users:(("nginx",pid=1,fd=1))';;
 own) echo 'LISTEN 0 4096 127.0.0.1:8088 0.0.0.0:* users:(("docker-proxy",pid=1,fd=1))';;
esac
MOCK
chmod +x "$mock/docker" "$mock/ss"
export PATH="$mock:$PATH"
for scenario in free host foreign own own_foreign_listener; do
    export SCENARIO="$scenario"
    if bash /opt/carlosandre-portfolio/scripts/production/preflight.sh; then result=0; else result=$?; fi
    case "$scenario" in free|own) [[ "$result" == 0 ]];; *) [[ "$result" != 0 ]];; esac
done
echo 'PASS: preflight free port, foreign host/container, owned port and foreign listener with own project'
