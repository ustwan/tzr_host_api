#!/usr/bin/env bash
set -euo pipefail

# Usage: DOMAIN=api.tzrl.ru EMAIL=admin@example.com API_ALLOW_CIDRS='["1.2.3.4/32","5.6.7.0/24"]' WEBHOOK_ALLOW_CIDRS='["149.154.160.0/20","91.108.4.0/22"]' bash scripts/setup_edge_proxy.sh

command -v docker >/dev/null 2>&1 || { echo "Docker required" >&2; exit 1; }

docker network inspect edge_net >/dev/null 2>&1 || docker network create edge_net

export EMAIL="${EMAIL:-admin@example.com}"
export API_ALLOW_CIDRS="${API_ALLOW_CIDRS:-[\"1.2.3.4/32\"]}"
export WEBHOOK_ALLOW_CIDRS="${WEBHOOK_ALLOW_CIDRS:-[\"149.154.160.0/20\",\"91.108.4.0/22\"]}"

sudo mkdir -p traefik/letsencrypt traefik/dynamic
sudo touch traefik/letsencrypt/acme.json && sudo chmod 600 traefik/letsencrypt/acme.json

docker compose -f docker-compose.traefik.yml --project-name ${PROJECT_NAME_TRAEFIK:-proxy} up -d

echo "Traefik up on ports 80/443. Attach your services to edge_net with labels."
