#!/bin/sh
set -e

RSYNC_HOST=${RSYNC_HOST:-btl_rsyncd}
RSYNC_PORT=${RSYNC_PORT:-873}
LOGS_BASE=${LOGS_BASE:-/srv/btl_mirror}
SYNC_INTERVAL=${SYNC_INTERVAL:-60}

echo "Starting btl_syncer: ${RSYNC_HOST}:${RSYNC_PORT} -> ${LOGS_BASE}"

while true; do
    echo "$(date): Syncing logs..."
    mkdir -p ${LOGS_BASE}
    rsync -avz --delete --timeout=30 rsync://${RSYNC_HOST}:${RSYNC_PORT}/btl/ ${LOGS_BASE}/ || echo "Sync failed, retrying in 10s..."
    sleep ${SYNC_INTERVAL}
done
