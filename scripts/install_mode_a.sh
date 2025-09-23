#!/usr/bin/env bash
set -euo pipefail

# Mode A: Keep tuna external; use Traefik only inside VPN (10.8.0.1:443)
# Requirements: Linux, Docker, UDP/51820 open/forwarded to this host, /dev/net/tun available
# Usage:
#   WG_HOST=<PUBLIC_IP_OR_DNS_OF_HOST1> [ENABLE_VPN_DASH=1] [ENABLE_LAN_DASH=1 LAN_HOST_IP=172.16.16.104 LAN_DASH_PORT=9001] bash scripts/install_mode_a.sh

[ "$(uname -s)" = "Linux" ] || { echo "Run on Linux" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker required" >&2; exit 1; }

WG_HOST="${WG_HOST:-}"; [ -n "$WG_HOST" ] || { echo "Set WG_HOST (public IP/DNS for clients)" >&2; exit 1; }
ENABLE_VPN_DASH="${ENABLE_VPN_DASH:-0}"
ENABLE_LAN_DASH="${ENABLE_LAN_DASH:-0}"
LAN_HOST_IP="${LAN_HOST_IP:-}"      # e.g. 172.16.16.104
LAN_DASH_PORT="${LAN_DASH_PORT:-9001}"

# Enable forwarding
if [ ! -f /etc/sysctl.d/99-wg.conf ]; then
  echo "net.ipv4.ip_forward=1" | sudo tee /etc/sysctl.d/99-wg.conf >/dev/null
fi
sudo sysctl --system | grep net.ipv4.ip_forward || true

# wg-easy (host)
sudo mkdir -p /opt/wg-easy && sudo chmod 700 /opt/wg-easy
(docker ps --format '{{.Names}}' | grep -q '^wg-easy$') && docker rm -f wg-easy || true

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

# Ensure external networks for Traefik if defined
docker network inspect apinet >/dev/null 2>&1 || docker network create apinet

# Build override for dashboard exposure
OVR="traefik/docker-compose.override.yml"
mkdir -p traefik
: > "$OVR"

if [ "$ENABLE_VPN_DASH" = "1" ]; then
cat >> "$OVR" <<'YAML'
services:
  traefik:
    command:
      - --api.dashboard=true
      - --api.insecure=true
    ports:
      - target: 8080
        published: 9001
        protocol: tcp
        host_ip: 10.8.0.1
YAML
fi

if [ "$ENABLE_LAN_DASH" = "1" ]; then
  [ -n "$LAN_HOST_IP" ] || { echo "Set LAN_HOST_IP for LAN dashboard" >&2; exit 1; }
cat >> "$OVR" <<YAML
services:
  traefik:
    command:
      - --api.dashboard=true
      - --api.insecure=true
    ports:
      - target: 8080
        published: ${LAN_DASH_PORT}
        protocol: tcp
        host_ip: ${LAN_HOST_IP}
YAML
fi

# Internal Traefik bound to 10.8.0.1:443
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)/traefik"
if [ -s "../traefik/docker-compose.override.yml" ]; then
  sudo docker compose -f docker-compose.yml -f ../traefik/docker-compose.override.yml up -d
else
  sudo docker compose -f docker-compose.yml up -d
fi

# Status
sleep 2
docker ps --format 'table {{.Names}}\t{{.Status}}'
echo "Mode A ready. Dashboard flags: VPN=${ENABLE_VPN_DASH}, LAN=${ENABLE_LAN_DASH}."
