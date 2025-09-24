#!/usr/bin/env bash
set -euo pipefail

# Mode B: External Traefik on 80/443 (ACME), replace tuna
# Usage:
#   set -a; source ./env.example || true; set +a
#   WG_HOST=<PUBLIC_IP_OR_DNS_OF_HOST1> DOMAIN=api.example.com EMAIL=admin@example.com \
#   API_ALLOW_CIDRS='["1.2.3.4/32","5.6.7.0/24"]' WEBHOOK_ALLOW_CIDRS='["149.154.160.0/20","91.108.4.0/22"]' \
#   [VPN_CIDR=10.8.0.0/24] \
#   bash scripts/install_mode_b.sh

[ "$(uname -s)" = "Linux" ] || { echo "Run on Linux" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker required" >&2; exit 1; }

WG_HOST="${WG_HOST:-}"; [ -n "$WG_HOST" ] || { echo "Set WG_HOST" >&2; exit 1; }
DOMAIN="${DOMAIN:-}"; [ -n "$DOMAIN" ] || { echo "Set DOMAIN" >&2; exit 1; }
EMAIL="${EMAIL:-}"; [ -n "$EMAIL" ] || { echo "Set EMAIL" >&2; exit 1; }
API_ALLOW_CIDRS="${API_ALLOW_CIDRS:-[\"127.0.0.1/32\"]}"
WEBHOOK_ALLOW_CIDRS="${WEBHOOK_ALLOW_CIDRS:-[\"149.154.160.0/20\",\"91.108.4.0/22\"]}"
VPN_CIDR="${VPN_CIDR:-10.8.0.0/24}"

# Enable forwarding
echo "net.ipv4.ip_forward=1" | sudo tee /etc/sysctl.d/99-wg.conf >/dev/null
sudo sysctl --system | grep net.ipv4.ip_forward || true

# edge_net
(docker network inspect edge_net >/dev/null 2>&1) || docker network create edge_net

# wg-easy
sudo mkdir -p /opt/wg-easy && sudo chmod 700 /opt/wg-easy
(docker ps --format '{{.Names}}' | grep -q '^wg-easy$') && docker rm -f wg-easy || true

docker run -d \
  --name wg-easy \
  --network host \
  --cap-add NET_ADMIN --cap-add SYS_MODULE \
  -e WG_HOST="$WG_HOST" \
  -e WG_PORT=51820 \
  -e WG_DEFAULT_DNS=1.1.1.1 \
  -e WG_ALLOWED_IPS="$VPN_CIDR" \
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

# Traefik external (80/443)
sudo mkdir -p /opt/edge-proxy/letsencrypt /opt/edge-proxy/dynamic
sudo touch /opt/edge-proxy/letsencrypt/acme.json && sudo chmod 600 /opt/edge-proxy/letsencrypt/acme.json
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

(docker ps --format '{{.Names}}' | grep -q '^traefik-vpn-external$') && docker rm -f traefik-vpn-external || true

docker run -d \
  --name traefik-vpn-external \
  --network edge_net \
  -p 80:80 -p 443:443 \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /opt/edge-proxy/letsencrypt:/letsencrypt \
  -v /opt/edge-proxy/dynamic:/etc/traefik/dynamic \
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

sleep 2
docker ps --format 'table {{.Names}}\t{{.Status}}'
echo "Mode B ready. VPN_CIDR=${VPN_CIDR}. Attach services to edge_net with labels."
