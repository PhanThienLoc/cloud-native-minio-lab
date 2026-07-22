#!/usr/bin/env bash
set -euo pipefail

: "${MINIO_ALIAS:=local}"
: "${MINIO_ENDPOINT:=http://localhost:9000}"
: "${MINIO_ACCESS_KEY:=minioadmin}"
: "${MINIO_SECRET_KEY:=minioadmin123}"
: "${MINIO_BUCKET:=lake-raw}"

mc alias set "${MINIO_ALIAS}" "${MINIO_ENDPOINT}" "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}"
mc mb --ignore-existing "${MINIO_ALIAS}/${MINIO_BUCKET}"
