#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="/opt/wg-hub"
CONFIG_DIR="${TARGET_DIR}/config"
WG_DIR="${CONFIG_DIR}/wg_confs"
PEERS_DIR="${CONFIG_DIR}/peers"
CONTAINER_NAME="wg-hub"
NETWORK_CIDR="10.8.0.0/24"
HUB_IP="10.8.0.1"

usage() {
  cat <<USAGE
Usage: $0 <command> [args]
Commands:
  add <peer_name>           Add new peer, auto-assign IP, print client config
  list                      List peers with IPs
  show <peer_name>          Show peer block
  delete <peer_name>        Remove peer and its keys
USAGE
}

require_files() {
  [ -f "${WG_DIR}/wg0.conf" ] || { echo "wg0.conf not found in ${WG_DIR}" >&2; exit 1; }
  [ -f "${CONFIG_DIR}/server.pub" ] || { echo "server.pub not found in ${CONFIG_DIR}" >&2; exit 1; }
  sudo mkdir -p "${PEERS_DIR}"
}

next_ip() {
  # Scan existing AllowedIPs, find next free in 10.8.0.2..254
  used=$(grep -E "^AllowedIPs = 10\\.8\\.0\\.[0-9]+/32" -o "${WG_DIR}/wg0.conf" | awk '{print $3}' | cut -d'/' -f1 | cut -d'.' -f4 | sort -n | tr '\n' ' ')
  for i in $(seq 2 254); do
    if ! grep -q " 10.8.0.${i}/32" <<<"$used"; then
      echo "10.8.0.${i}"
      return 0
    fi
  done
  echo "No free IPs in ${NETWORK_CIDR}" >&2; exit 1
}

add_peer() {
  local name="$1"
  require_files
  local ip
  ip=$(next_ip)

  # keys via running container
  sudo docker exec -i "${CONTAINER_NAME}" bash -lc "cd /config/peers && umask 077 && wg genkey | tee ${name}.key | wg pubkey > ${name}.pub"
  local peer_pub peer_priv server_pub endpoint
  peer_pub=$(sudo cat "${PEERS_DIR}/${name}.pub")
  peer_priv=$(sudo cat "${PEERS_DIR}/${name}.key")
  server_pub=$(sudo cat "${CONFIG_DIR}/server.pub")
  endpoint="<HOST1_PUBLIC_IP_OR_DNS>:51820"

  sudo tee -a "${WG_DIR}/wg0.conf" >/dev/null <<EOF

[Peer]
# ${name}
PublicKey = ${peer_pub}
AllowedIPs = ${ip}/32
EOF

  # restart to apply
  (cd "${TARGET_DIR}" && sudo docker compose restart >/dev/null)

  cat <<CLIENT
# ----- CLIENT CONFIG: ${name} -----
[Interface]
Address = ${ip}/32
PrivateKey = ${peer_priv}
DNS = 1.1.1.1

[Peer]
PublicKey = ${server_pub}
Endpoint = ${endpoint}
AllowedIPs = ${NETWORK_CIDR}
PersistentKeepalive = 25
CLIENT
}

list_peers() {
  awk '/^\[Peer\]/{peer=1;ip="";name="";pub="";next}
       peer && /^# /{name=$0; sub(/^# /, "", name); next}
       peer && /^PublicKey/{pub=$3; next}
       peer && /^AllowedIPs/{ip=$3; print name"\t"ip; peer=0 }' "${WG_DIR}/wg0.conf" || true
}

show_peer() {
  local name="$1"
  awk "/# ${name}/{flag=1} flag{print} /^$/ && flag{exit}" "${WG_DIR}/wg0.conf" || { echo "Peer not found: ${name}" >&2; exit 1; }
}

delete_peer() {
  local name="$1"
  sudo awk -v name="${name}" '
    BEGIN{keep=1}
    /^\[Peer\]/{ if(block){ if(!skip) print block; block="" } block=$0"\n"; skip=0; next }
    { if(block){ block=block $0"\n"; if($0 ~ /^# /){ n=$0; sub(/^# /, "", n); if(n==name){ skip=1 } } }
      else { print } }
    END{ if(block && !skip) print block }
  ' "${WG_DIR}/wg0.conf" | sudo tee "${WG_DIR}/wg0.conf.tmp" >/dev/null
  sudo mv "${WG_DIR}/wg0.conf.tmp" "${WG_DIR}/wg0.conf"
  sudo rm -f "${PEERS_DIR}/${name}.key" "${PEERS_DIR}/${name}.pub" || true
  (cd "${TARGET_DIR}" && sudo docker compose restart >/dev/null)
  echo "Peer ${name} removed"
}

cmd="${1:-}" || true
case "$cmd" in
  add)    shift; [ $# -eq 1 ] || { usage; exit 1; }; add_peer "$1" ;;
  list)   shift; list_peers ;;
  show)   shift; [ $# -eq 1 ] || { usage; exit 1; }; show_peer "$1" ;;
  delete) shift; [ $# -eq 1 ] || { usage; exit 1; }; delete_peer "$1" ;;
  *) usage; exit 1;;
esac
