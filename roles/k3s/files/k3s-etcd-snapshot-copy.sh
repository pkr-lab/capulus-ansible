#!/usr/bin/env bash
set -euo pipefail

SNAPSHOT_DIR="${SNAPSHOT_DIR:?not set}"
MOUNT_POINT="${MOUNT_POINT:?not set}"
KEEP_DAYS="${KEEP_DAYS:?not set}"
NODE_NAME="${NODE_NAME:?not set}"

if ! mountpoint -q "$MOUNT_POINT"; then
  logger -t k3s-etcd-snapshot-copy "ERROR: ${MOUNT_POINT} ist nicht eingebunden"
  exit 1
fi

if ! ls "$SNAPSHOT_DIR"/* > /dev/null 2>&1; then
  logger -t k3s-etcd-snapshot-copy "ERROR: keine Snapshots in ${SNAPSHOT_DIR}"
  exit 1
fi

dest="${MOUNT_POINT}/${NODE_NAME}"
mkdir -p "$dest"
rsync -a --ignore-existing "${SNAPSHOT_DIR}/" "${dest}/"
find "$dest" -type f -mtime +"$KEEP_DAYS" -delete

count="$(find "$dest" -type f | wc -l)"
logger -t k3s-etcd-snapshot-copy "ok: ${count} Snapshots in ${dest}"
