#!/bin/bash

echo "=========================================="
echo "Starting UnifiedLayer Backend"
echo "=========================================="

echo ""
echo "Step 1: Running database migrations..."
cd /app
python3 -m alembic upgrade head || {
    echo "WARNING: Migrations failed, continuing anyway..."
}

echo ""
echo "Step 2: Seeding RBAC roles..."
python3 -m backend.scripts.seed_rbac || {
    echo "WARNING: RBAC seeding skipped (may already exist)"
}

echo ""
echo "Step 3: Creating/updating super admin..."
export SUPER_ADMIN_PASSWORD="${SUPER_ADMIN_PASSWORD:-Admin123!}"
python3 -m backend.scripts.create_super_admin --env || {
    echo "WARNING: Super admin creation skipped"
}

echo ""
echo "Step 4: Starting uvicorn on port ${PORT:-8000}..."
echo "=========================================="
exec python3 -m uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
