#!/usr/bin/env bash
set -euo pipefail

: "${MINIO_ALIAS:=myminio}"
: "${MINIO_ENDPOINT:=http://localhost:9000}"
if [ -z "${MINIO_ROOT_USER:-}" ]; then
    echo "ERROR: MINIO_ROOT_USER is not set"
    exit 1
fi

if [ -z "${MINIO_ROOT_PASSWORD:-}" ]; then
    echo "ERROR: MINIO_ROOT_PASSWORD is not set"
    exit 1
fi
: "${MINIO_BUCKET_RAW:=raw-data}"
: "${MINIO_BUCKET_PROCESSED:=processed-data}"
: "${MINIO_BUCKET_LOGS:=system-logs}"

echo "Creating alias..."
mc alias set \
    "${MINIO_ALIAS}" \
    "${MINIO_ENDPOINT}" \
    "${MINIO_ROOT_USER}" \
    "${MINIO_ROOT_PASSWORD}"


echo "Creating buckets..."    
mc mb --ignore-existing "${MINIO_ALIAS}/${MINIO_BUCKET_RAW}"
mc mb --ignore-existing "${MINIO_ALIAS}/${MINIO_BUCKET_PROCESSED}"
mc mb --ignore-existing "${MINIO_ALIAS}/${MINIO_BUCKET_LOGS}"

mc version enable "${MINIO_ALIAS}/${MINIO_BUCKET_RAW}"

echo "====================================="
echo "MinIO setup completed successfully!"
echo "Buckets created:"
echo "- ${MINIO_BUCKET_RAW}"
echo "- ${MINIO_BUCKET_PROCESSED}"
echo "- ${MINIO_BUCKET_LOGS}"
echo "Versioning enabled for: ${MINIO_BUCKET_RAW}"
echo "====================================="

echo
echo "Available buckets:"
mc ls "${MINIO_ALIAS}"

echo
echo "Version information:"

echo "Enabling versioning..."
mc version info "${MINIO_ALIAS}/${MINIO_BUCKET_RAW}"