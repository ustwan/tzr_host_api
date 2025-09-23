#!/usr/bin/env bash
set -euo pipefail

# One-step setup for WireGuard HUB on HOST_1 (Linux)
# - Prepares /opt/wg-hub structure
# - Ensures docker compose file present
# - Generates server keys if missing
# - Writes /opt/wg-hub/config/wg_confs/wg0.conf without sysctl PostUp
# - Enables IP forwarding on host
# - Starts container and prints status

if [ "$(uname -s)" = "Darwin" ]; then
  echo "This setup script is for Linux HOST_1 only." >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
TARGET_DIR="/opt/wg-hub"
CONFIG_DIR="${TARGET_DIR}/config"
WG_DIR="${CONFIG_DIR}/wg_confs"
COMPOSE_SRC="${REPO_ROOT}/opt/wg-hub/docker-compose.yml"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker Engine and docker compose plugin." >&2
  exit 1
fi

sudo mkdir -p "${WG_DIR}"
sudo chown -R root:root "${TARGET_DIR}" "${CONFIG_DIR}" "${WG_DIR}" || true
sudo chmod 700 "${CONFIG_DIR}"

# Place compose
if [ ! -f "${TARGET_DIR}/docker-compose.yml" ]; then
  sudo install -m 644 "${COMPOSE_SRC}" "${TARGET_DIR}/docker-compose.yml"
fi

# Generate server keys (host wg or via container)
if [ ! -f "${CONFIG_DIR}/server.key" ]; then
  if command -v wg >/dev/null 2>&1; then
    sudo sh -c "cd '${CONFIG_DIR}' && umask 077 && wg genkey | tee server.key | wg pubkey > server.pub"
  else
    echo "wg not found on host. Generating keys via running container image..."
    sudo docker run --rm -v "${CONFIG_DIR}:/config" lscr.io/linuxserver/wireguard:latest \
      bash -lc "cd /config && umask 077 && wg genkey | tee server.key | wg pubkey > server.pub"
  fi
fi
sudo chmod 600 "${CONFIG_DIR}/server.key"

# Write wg0.conf (no sysctl here)
SERVER_KEY_CONTENT=$(sudo cat "${CONFIG_DIR}/server.key")
sudo tee "${WG_DIR}/wg0.conf" >/dev/null <<EOF
[Interface]
Address = 10.8.0.1/24
ListenPort = 51820
PrivateKey = ${SERVER_KEY_CONTENT}

PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -A FORWARD -o wg0 -j ACCEPT
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -D FORWARD -o wg0 -j ACCEPT
EOF
sudo chmod 600 "${WG_DIR}/wg0.conf"

# Enable host IP forwarding persistently
echo "net.ipv4.ip_forward=1" | sudo tee /etc/sysctl.d/99-wg-forward.conf >/dev/null
sudo sysctl --system | grep net.ipv4.ip_forward || true

# Start
cd "${TARGET_DIR}"
sudo docker compose up -d
sleep 2
sudo docker compose ps
sudo docker logs --tail=100 wg-hub | cat
sudo docker exec -it wg-hub wg show || true

echo "WG HUB ready. Use scripts/peer_admin.sh to add peers."
