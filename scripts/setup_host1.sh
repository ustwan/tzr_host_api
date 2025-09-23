#!/usr/bin/env bash
set -euo pipefail

[ "$(uname -s)" = "Linux" ] || { echo "Run on Linux HOST_1" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker required" >&2; exit 1; }

# 1) Enable forwarding
echo "net.ipv4.ip_forward=1" | sudo tee /etc/sysctl.d/99-wg.conf >/dev/null
sudo sysctl --system | grep net.ipv4.ip_forward || true

# 2) Prepare wg-easy data dir
sudo mkdir -p /opt/wg-easy
sudo chown root:root /opt/wg-easy
sudo chmod 700 /opt/wg-easy

# 3) Deploy wg-easy (host network)
WG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)/wg-easy"
cd "$WG_DIR"
sudo docker compose up -d

# 4) Deploy Traefik (bind 10.8.0.1:443)
TRAEFIK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)/traefik"
cd "$TRAEFIK_DIR"
sudo docker compose up -d

# 5) Show status
sudo docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
