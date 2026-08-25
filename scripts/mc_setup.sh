#!/usr/bin/env bash
set -euo pipefail

: "${MINIO_ALIAS:=local}"
: "${MINIO_ENDPOINT:=http://localhost:9000}"
: "${MINIO_ACCESS_KEY:=minioadmin}"
: "${MINIO_SECRET_KEY:=minioadmin123}"

mc alias set "${MINIO_ALIAS}" \
  "${MINIO_ENDPOINT}" \
  "${MINIO_ACCESS_KEY}" \
  "${MINIO_SECRET_KEY}"

for bucket in raw-data processed-data system-logs; do
    echo "==> Creating bucket: ${bucket}"
    mc mb --ignore-existing "${MINIO_ALIAS}/${bucket}"
done

echo "==> Enabling versioning for raw-data..."
mc version enable "${MINIO_ALIAS}/raw-data"

echo "==> Current buckets:"
mc ls "${MINIO_ALIAS}"

echo "==> Versioning status:"
mc version info "${MINIO_ALIAS}/raw-data"

echo "==> mc setup completed successfully."