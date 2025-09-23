#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="/opt/wg-hub"
CONFIG_DIR="${TARGET_DIR}/config"
WG_DIR="${CONFIG_DIR}/wg_confs"
COMPOSE_FILE="${TARGET_DIR}/docker-compose.yml"
CONTAINER_NAME="wg-hub"

usage() {
  cat <<USAGE
Usage: $0 <command> [args]
Commands:
  add <peer_name>           Add a new peer, output client config
  list                      List existing peers (names)
  show <peer_name>          Show peer public key and AllowedIPs
  delete <peer_name>        Remove peer from wg0.conf and keys

USAGE
}

ensure_ready() {
  [ -f "${WG_DIR}/wg0.conf" ] || { echo "wg0.conf not found in ${WG_DIR}" >&2; exit 1; }
}

add_peer() {
  local name="$1"
  local peers_dir="${CONFIG_DIR}/peers"
  sudo mkdir -p "${peers_dir}"
  # generate peer keys inside container to avoid host deps
  sudo docker exec -i "${CONTAINER_NAME}" bash -lc "cd /config/peers && umask 077 && wg genkey | tee ${name}.key | wg pubkey > ${name}.pub"
  local peer_pub
  peer_pub=$(sudo cat "${peers_dir}/${name}.pub")

  # append to wg0.conf
  sudo tee -a "${WG_DIR}/wg0.conf" >/dev/null <<EOF

[Peer]
# ${name}
PublicKey = ${peer_pub}
AllowedIPs = 10.8.0.0/32
EOF

  # restart container
  cd "${TARGET_DIR}" && sudo docker compose up -d && sudo docker compose restart >/dev/null

  # build client config to stdout
  local server_pub
  server_pub=$(sudo cat "${CONFIG_DIR}/server.pub")
  local endpoint
  endpoint="<HOST1_PUBLIC_IP_OR_DNS>:51820"

  echo "----- CLIENT CONFIG (${name}) -----"
  cat <<CLIENT
[Interface]
Address = 10.8.0.0/32
PrivateKey = $(sudo cat "${peers_dir}/${name}.key")
DNS = 1.1.1.1

[Peer]
PublicKey = ${server_pub}
Endpoint = ${endpoint}
AllowedIPs = 10.8.0.0/24
PersistentKeepalive = 25
CLIENT
}

list_peers() {
  grep -n "^# " "${WG_DIR}/wg0.conf" | sed 's/^.*# \(.*\)$/\1/' || true
}

show_peer() {
  local name="$1"
  awk "/# ${name}/{flag=1;print;next}/^\[Peer\]/{if(flag){exit}}flag" "${WG_DIR}/wg0.conf" || {
    echo "Peer not found: ${name}" >&2; exit 1; }
}

delete_peer() {
  local name="$1"
  sudo awk -v name="${name}" '
    BEGIN{p=0}
    /^\[Peer\]/{ if(p==1){p=0; next} }
    /# /{ if($2==name){ p=1; next } }
    { if(p==0) print }
  ' "${WG_DIR}/wg0.conf" | sudo tee "${WG_DIR}/wg0.conf.tmp" >/dev/null
  sudo mv "${WG_DIR}/wg0.conf.tmp" "${WG_DIR}/wg0.conf"
  sudo rm -f "${CONFIG_DIR}/peers/${name}.key" "${CONFIG_DIR}/peers/${name}.pub" || true
  cd "${TARGET_DIR}" && sudo docker compose restart >/dev/null
  echo "Peer ${name} removed"
}

cmd="${1:-}" || true
case "${cmd}" in
  add)    shift; [ $# -eq 1 ] || { usage; exit 1; }; ensure_ready; add_peer "$1" ;;
  list)   shift; ensure_ready; list_peers ;;
  show)   shift; [ $# -eq 1 ] || { usage; exit 1; }; ensure_ready; show_peer "$1" ;;
  delete) shift; [ $# -eq 1 ] || { usage; exit 1; }; ensure_ready; delete_peer "$1" ;;
  *) usage; exit 1;;
 esac
