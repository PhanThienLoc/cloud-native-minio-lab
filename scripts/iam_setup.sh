#!/bin/bash

set -euo pipefail

ALIAS="${MINIO_ALIAS:-local}"

ADMIN_USER="${ADMIN_USER:-admin-user}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-Admin@123456}"

DEV_USER="${DEV_USER:-dev-user}"
DEV_PASSWORD="${DEV_PASSWORD:-Dev@123456}"

READONLY_USER="${READONLY_USER:-readonly-user}"
READONLY_PASSWORD="${READONLY_PASSWORD:-Readonly@123456}"

echo "========================================"
echo "          MINIO IAM SETUP"
echo "========================================"

echo "[1/5] Creating policies..."

mc admin policy create "$ALIAS" \
    admin-policy \
    ./policies/admin-policy.json || true

mc admin policy create "$ALIAS" \
    dev-policy \
    ./policies/dev-policy.json || true

mc admin policy create "$ALIAS" \
    readonly-policy \
    ./policies/readonly-policy.json || true


echo "[2/5] Creating users..."

mc admin user add "$ALIAS" \
    "$ADMIN_USER" "$ADMIN_PASSWORD" || true

mc admin user add "$ALIAS" \
    "$DEV_USER" "$DEV_PASSWORD" || true

mc admin user add "$ALIAS" \
    "$READONLY_USER" "$READONLY_PASSWORD" || true


echo "[3/5] Attaching policies..."

mc admin policy attach "$ALIAS" \
    admin-policy --user "$ADMIN_USER"

mc admin policy attach "$ALIAS" \
    dev-policy --user "$DEV_USER"

mc admin policy attach "$ALIAS" \
    readonly-policy --user "$READONLY_USER"


echo "[4/5] Enabling versioning..."

mc version enable "$ALIAS/raw-data"


echo "[5/5] Configuring lifecycle..."

mc ilm rule add \
    --expire-days 30 \
    "$ALIAS/system-logs" || true


echo "========================================"
echo "       IAM SETUP COMPLETED"
echo "========================================"