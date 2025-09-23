#!/usr/bin/env bash
set -euo pipefail

# Mode A: Keep tuna external; use Traefik only inside VPN (10.8.0.1:443)
# Requirements: Linux, Docker, UDP/51820 open/forwarded to this host, /dev/net/tun available
# Usage:
#   WG_HOST=<PUBLIC_IP_OR_DNS_OF_HOST1> bash scripts/install_mode_a.sh

[ "$(uname -s)" = "Linux" ] || { echo "Run on Linux" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker required" >&2; exit 1; }

WG_HOST="${WG_HOST:-}"; [ -n "$WG_HOST" ] || { echo "Set WG_HOST (public IP/DNS for clients)" >&2; exit 1; }

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

# Internal Traefik bound to 10.8.0.1:443
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)/traefik"
sudo docker compose up -d

# Status
sleep 2
docker ps --format 'table {{.Names}}\t{{.Status}}'
echo "Mode A: wg-easy up (UDP/51820); internal Traefik on 10.8.0.1:443. Tuna remains external."
