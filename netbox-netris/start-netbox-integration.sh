#!/usr/bin/env bash
# Brings up NetBox (seeded with sample AI-cluster IPAM data) + the NetBox<->Netris
# sync service via Docker Compose. Safe to re-run - it's idempotent.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if ! command -v docker &>/dev/null; then
  echo "Error: docker is not installed or not on PATH." >&2
  exit 1
fi

if ! docker compose version &>/dev/null; then
  echo "Error: the 'docker compose' v2 plugin is required (not the standalone docker-compose v1)." >&2
  exit 1
fi

if [ ! -f .env ]; then
  echo "No .env found - copying .env.example -> .env." >&2
  cp .env.example .env
  echo "Edit .env with real secrets (Netris URL/creds, NetBox tokens), then re-run this script." >&2
  exit 1
fi

mkdir -p data/postgres data/redis data/redis-cache data/netbox-media data/netbox-reports data/netbox-scripts data/sync-service

echo "Starting NetBox + Netris sync stack..."
docker compose up -d --build

echo
echo -n "Waiting for NetBox to become healthy (first boot can take a couple of minutes)"
tries=0
until [ "$(docker inspect -f '{{.State.Health.Status}}' "$(docker compose ps -q netbox)" 2>/dev/null || true)" = "healthy" ]; do
  tries=$((tries + 1))
  if [ "$tries" -gt 60 ]; then
    echo
    echo "NetBox did not become healthy in time. Check: docker compose logs netbox" >&2
    exit 1
  fi
  printf '.'
  sleep 5
done
echo

echo
echo "NetBox UI:      http://localhost:8000  (user: admin, password: see NETBOX_SUPERUSER_PASSWORD in .env)"
echo "Sync status:    http://localhost:8090/status"
echo
echo "Logs:           docker compose logs -f sync-service"
echo "Stop:           docker compose down"
