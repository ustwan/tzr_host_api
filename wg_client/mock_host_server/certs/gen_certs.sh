#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Параметры
DAYS=${DAYS:-3650}
CN_BASE=${CN_BASE:-wg-host-server}

mkdir -p ca server client_register client_readonly client_admin

# CA
openssl req -x509 -new -nodes -days $DAYS -subj "/CN=${CN_BASE}_CA" -keyout ca/ca.key -out ca/ca.crt -sha256

# Server key/cert
openssl genrsa -out server/server.key 2048
openssl req -new -key server/server.key -subj "/CN=${CN_BASE}_db_bridge" -out server/server.csr
openssl x509 -req -in server/server.csr -CA ca/ca.crt -CAkey ca/ca.key -CAcreateserial -out server/server.crt -days $DAYS -sha256

# Client register
openssl genrsa -out client_register/client.key 2048
openssl req -new -key client_register/client.key -subj "/CN=api_register" -out client_register/client.csr
openssl x509 -req -in client_register/client.csr -CA ca/ca.crt -CAkey ca/ca.key -CAcreateserial -out client_register/client.crt -days $DAYS -sha256

# Client readonly
openssl genrsa -out client_readonly/client.key 2048
openssl req -new -key client_readonly/client.key -subj "/CN=api_readonly" -out client_readonly/client.csr
openssl x509 -req -in client_readonly/client.csr -CA ca/ca.crt -CAkey ca/ca.key -CAcreateserial -out client_readonly/client.crt -days $DAYS -sha256

# Client admin
openssl genrsa -out client_admin/client.key 2048
openssl req -new -key client_admin/client.key -subj "/CN=api_admin" -out client_admin/client.csr
openssl x509 -req -in client_admin/client.csr -CA ca/ca.crt -CAkey ca/ca.key -CAcreateserial -out client_admin/client.crt -days $DAYS -sha256

echo "Certificates generated under $(pwd)"
echo "  - CA: ca/ca.crt, ca/ca.key"
echo "  - Server: server/server.crt, server/server.key"
echo "  - Client register: client_register/client.crt, client_register/client.key"
echo "  - Client readonly: client_readonly/client.crt, client_readonly/client.key"
echo "  - Client admin: client_admin/client.crt, client_admin/client.key"
