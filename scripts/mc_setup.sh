#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
if [[ -f "${ROOT_DIR}/.env" ]]; then
  set -a
  # The local .env contains simple KEY=value assignments for this lab.
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env"
  set +a
fi

MINIO_ALIAS="${MINIO_ALIAS:-myminio}"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-${ENDPOINT_URL:-http://localhost:9000}}"
ACCESS_KEY="${AWS_ACCESS_KEY_ID:-${MINIO_ROOT_USER:-}}"
SECRET_KEY="${AWS_SECRET_ACCESS_KEY:-${MINIO_ROOT_PASSWORD:-}}"

if [[ -z "${ACCESS_KEY}" || -z "${SECRET_KEY}" ]]; then
  echo "ERROR: set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY or MINIO_ROOT_USER/MINIO_ROOT_PASSWORD" >&2
  exit 1
fi

if [[ "${ACCESS_KEY}" == change-me* || "${SECRET_KEY}" == change-me* ]]; then
  echo "ERROR: replace placeholder credentials before running mc_setup.sh" >&2
  exit 1
fi

if ! command -v mc >/dev/null 2>&1; then
  echo "ERROR: MinIO Client (mc) is required" >&2
  exit 1
fi

mc alias set "${MINIO_ALIAS}" "${MINIO_ENDPOINT}" "${ACCESS_KEY}" "${SECRET_KEY}"

for bucket in raw-data processed-data system-logs; do
  mc mb --ignore-existing "${MINIO_ALIAS}/${bucket}"
done

mc ls "${MINIO_ALIAS}"
