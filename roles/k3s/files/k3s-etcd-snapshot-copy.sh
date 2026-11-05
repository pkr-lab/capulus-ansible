#!/usr/bin/env bash
set -euo pipefail

SNAPSHOT_DIR="${SNAPSHOT_DIR:?not set}"
MOUNT_POINT="${MOUNT_POINT:?not set}"
KEEP_DAYS="${KEEP_DAYS:?not set}"
NODE_NAME="${NODE_NAME:?not set}"
NTFY_HOST="${NTFY_HOST:?not set}"
NTFY_IP="${NTFY_IP:?not set}"
NTFY_TOPIC="${NTFY_TOPIC:?not set}"
NTFY_AUTH_HEADER_FILE="${NTFY_AUTH_HEADER_FILE:-/etc/ntfy-publisher/auth-header}"
NTFY_CA_FILE="${NTFY_CA_FILE:-/etc/ntfy-publisher/ca.pem}"
ntfy_auth_args=()
if [ -r "$NTFY_AUTH_HEADER_FILE" ]; then
  ntfy_auth_args=(-H "@${NTFY_AUTH_HEADER_FILE}")
fi

fail() {
  logger -t k3s-etcd-snapshot-copy "ERROR: $1"
  curl --fail --silent --show-error --max-time 10 \
    --resolve "${NTFY_HOST}:443:${NTFY_IP}" \
    --cacert "$NTFY_CA_FILE" \
    "${ntfy_auth_args[@]}" \
    -H "Title: etcd-Snapshot-Kopie fehlgeschlagen" \
    -H "Priority: 4" \
    -H "Tags: warning,floppy_disk" \
    -d "${NODE_NAME}: $1" \
    "https://${NTFY_HOST}/${NTFY_TOPIC}" || logger -t k3s-etcd-snapshot-copy "ntfy-Meldung fehlgeschlagen"
  exit 1
}

trap 'fail "unerwarteter Fehler in Zeile ${LINENO}"' ERR

if ! mountpoint -q "$MOUNT_POINT"; then
  fail "${MOUNT_POINT} ist nicht eingebunden"
fi

if ! ls "$SNAPSHOT_DIR"/* > /dev/null 2>&1; then
  fail "keine Snapshots in ${SNAPSHOT_DIR}"
fi

dest="${MOUNT_POINT}/${NODE_NAME}"
mkdir -p "$dest"
rsync -rt --ignore-existing "${SNAPSHOT_DIR}/" "${dest}/"
find "$dest" -type f -mtime +"$KEEP_DAYS" -delete

count="$(find "$dest" -type f | wc -l)"
logger -t k3s-etcd-snapshot-copy "ok: ${count} Snapshots in ${dest}"
