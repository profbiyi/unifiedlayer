#!/bin/bash
set -e

echo "Running database migrations..."
python -m alembic upgrade head

echo "Seeding RBAC roles..."
python -m backend.scripts.seed_rbac || echo "RBAC seeding skipped (may already exist)"

echo "Creating super admin if not exists..."
SUPER_ADMIN_PASSWORD=${SUPER_ADMIN_PASSWORD:-Admin123!} python -m backend.scripts.create_super_admin --env || echo "Super admin creation skipped (may already exist)"

echo "Starting application..."
exec uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
