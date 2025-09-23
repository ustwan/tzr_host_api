#!/usr/bin/env bash
set -euo pipefail

# Quick setup (single file): wg-easy (host mode) + Traefik (TLS, IP whitelist)
# Usage example:
#   WG_HOST=your.public.ip.or.dns \
#   DOMAIN=api.example.com \
#   EMAIL=admin@example.com \
#   API_ALLOW_CIDRS='["1.2.3.4/32","5.6.7.0/24"]' \
#   WEBHOOK_ALLOW_CIDRS='["149.154.160.0/20","91.108.4.0/22"]' \
#   bash scripts/quick_setup.sh

[ "$(uname -s)" = "Linux" ] || { echo "Run on Linux host" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker required" >&2; exit 1; }

WG_HOST="${WG_HOST:-}"
DOMAIN="${DOMAIN:-}"
EMAIL="${EMAIL:-}"
API_ALLOW_CIDRS="${API_ALLOW_CIDRS:-[\"127.0.0.1/32\"]}"
WEBHOOK_ALLOW_CIDRS="${WEBHOOK_ALLOW_CIDRS:-[\"149.154.160.0/20\",\"91.108.4.0/22\"]}"

[ -n "$WG_HOST" ] || { echo "Set WG_HOST to your public IP/DNS" >&2; exit 1; }
[ -n "$DOMAIN" ] || { echo "Set DOMAIN (FQDN for TLS)" >&2; exit 1; }
[ -n "$EMAIL" ] || { echo "Set EMAIL (for Let’s Encrypt)" >&2; exit 1; }

# 1) Enable IP forwarding
if [ ! -f /etc/sysctl.d/99-wg.conf ]; then
  echo "net.ipv4.ip_forward=1" | sudo tee /etc/sysctl.d/99-wg.conf >/dev/null
fi
sudo sysctl --system | grep net.ipv4.ip_forward || true

# 2) Create external network for Traefik + services
if ! docker network inspect edge_net >/dev/null 2>&1; then
  docker network create edge_net
fi

# 3) wg-easy (host network)
sudo mkdir -p /opt/wg-easy
sudo chmod 700 /opt/wg-easy

docker ps --format '{{.Names}}' | grep -q '^wg-easy$' && docker rm -f wg-easy >/dev/null 2>&1 || true

docker run -d \
  --name wg-easy \
  --network host \
  --cap-add NET_ADMIN --cap-add SYS_MODULE \
  -e WG_HOST="$WG_HOST" \
  -e WG_PORT=51820 \
  -e WG_DEFAULT_DNS=1.1.1.1 \
  -e WG_ALLOWED_IPS=10.8.0.0/24 \
  -e WG_PERSISTENT_KEEPALIVE=25 \
  -e WG_DEVICE=wg0 \
  -e WG_MTU=1420 \
  -e WG_POST_UP='iptables -A FORWARD -i wg0 -j ACCEPT; iptables -A FORWARD -o wg0 -j ACCEPT' \
  -e WG_POST_DOWN='iptables -D FORWARD -i wg0 -j ACCEPT; iptables -D FORWARD -o wg0 -j ACCEPT' \
  -e UI_TRAFFIC_STATS=true \
  -e PORT=51821 \
  -v /opt/wg-easy:/etc/wireguard \
  --restart unless-stopped \
  weejewel/wg-easy:latest

# 4) Traefik (ports 80/443), ACME HTTP-01, file provider with IP whitelists
sudo mkdir -p /opt/edge-proxy/letsencrypt /opt/edge-proxy/dynamic
sudo touch /opt/edge-proxy/letsencrypt/acme.json && sudo chmod 600 /opt/edge-proxy/letsencrypt/acme.json

# dynamic middlewares
sudo tee /opt/edge-proxy/dynamic/middlewares.yml >/dev/null <<EOF
http:
  middlewares:
    api-allow:
      ipWhiteList:
        sourceRange: ${API_ALLOW_CIDRS}
    webhook-allow:
      ipWhiteList:
        sourceRange: ${WEBHOOK_ALLOW_CIDRS}
EOF

docker ps --format '{{.Names}}' | grep -q '^traefik-vpn-external$' && docker rm -f traefik-vpn-external >/dev/null 2>&1 || true

docker run -d \
  --name traefik-vpn-external \
  --network edge_net \
  -p 80:80 -p 443:443 \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /opt/edge-proxy/letsencrypt:/letsencrypt \
  -v /opt/edge-proxy/dynamic:/etc/traefik/dynamic \
  -e EMAIL="$EMAIL" \
  traefik:v3.0 \
  --providers.docker=true \
  --providers.docker.exposedbydefault=false \
  --providers.file.directory=/etc/traefik/dynamic \
  --entrypoints.web.address=:80 \
  --entrypoints.websecure.address=:443 \
  --certificatesresolvers.le.acme.httpchallenge=true \
  --certificatesresolvers.le.acme.httpchallenge.entrypoint=web \
  --certificatesresolvers.le.acme.email=$EMAIL \
  --certificatesresolvers.le.acme.storage=/letsencrypt/acme.json \
  --log.level=INFO

# 5) Hints
cat <<EON
Done.
- wg-easy up (UDP/51820; UI on 51821 — restrict via firewall).
- Traefik up on 80/443 with ACME. Attach your services to edge_net and add labels:
  traefik.enable=true
  traefik.http.routers.<name>.rule=Host(\`${DOMAIN}\`) && PathPrefix(\`/path\`)
  traefik.http.routers.<name>.entrypoints=websecure
  traefik.http.routers.<name>.tls.certresolver=le
  traefik.http.routers.<name>.middlewares=api-allow@file|webhook-allow@file
  traefik.http.services.<name>.loadbalancer.server.port=<container_port>
EON
