#!/bin/bash

echo "=========================================="
echo "Starting UnifiedLayer Backend"
echo "=========================================="

# Check if we should reset the database
if [ "$RESET_DATABASE" = "true" ]; then
    echo ""
    echo "WARNING: RESET_DATABASE=true - Dropping all tables..."
    python3 << 'EOF'
from sqlalchemy import create_engine, text
import os

db_url = os.environ.get("DATABASE_URL")
if db_url:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    print("Database reset complete!")
else:
    print("ERROR: DATABASE_URL not set")
EOF
    echo "Tables dropped. Running fresh migrations..."
fi

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
