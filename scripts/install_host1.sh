#!/usr/bin/env bash
set -euo pipefail

# Install/upgrade WG hub on HOST_1
# - Copies compose and config template to /opt/wg-hub
# - Generates server keys if missing
# - Injects PrivateKey into wg0.conf
# - Opens UDP/51820 via UFW if present
# - Starts container

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
TARGET_DIR="/opt/wg-hub"
CONFIG_DIR="${TARGET_DIR}/config"
COMPOSE_SRC="${REPO_ROOT}/opt/wg-hub/docker-compose.yml"
WGCONF_SRC="${REPO_ROOT}/opt/wg-hub/config/wg0.conf"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Please install Docker Engine and docker compose plugin." >&2
  exit 1
fi

sudo mkdir -p "${CONFIG_DIR}"
sudo chown root:root "${TARGET_DIR}" "${CONFIG_DIR}"
sudo chmod 700 "${CONFIG_DIR}"

# Copy compose and wg0 template if not present
if [ ! -f "${TARGET_DIR}/docker-compose.yml" ]; then
  sudo install -m 644 "${COMPOSE_SRC}" "${TARGET_DIR}/docker-compose.yml"
fi
if [ ! -f "${CONFIG_DIR}/wg0.conf" ]; then
  sudo install -m 600 "${WGCONF_SRC}" "${CONFIG_DIR}/wg0.conf"
fi

# Generate keys if missing
if [ ! -f "${CONFIG_DIR}/server.key" ]; then
  ( cd "${CONFIG_DIR}" && umask 077 && sudo sh -c 'wg genkey | tee server.key | wg pubkey > server.pub' )
  echo "Generated server keypair in ${CONFIG_DIR}"
fi
sudo chmod 600 "${CONFIG_DIR}/server.key"

# Inject PrivateKey into wg0.conf
SERVER_KEY_CONTENT=$(sudo cat "${CONFIG_DIR}/server.key")
sudo sed -i.bak "s|^PrivateKey = .*|PrivateKey = ${SERVER_KEY_CONTENT}|" "${CONFIG_DIR}/wg0.conf"

# Optionally open UFW 51820/udp
if command -v ufw >/dev/null 2>&1; then
  sudo ufw allow 51820/udp || true
  sudo ufw reload || true
fi

# Start service
cd "${TARGET_DIR}"
sudo docker compose up -d

# Show status
sudo docker compose ps
sudo docker logs --tail=100 wg-hub | cat
sudo docker exec -it wg-hub wg show || true

echo "WireGuard hub is up. Place HOST_2 public key into wg0.conf and restart if needed."
