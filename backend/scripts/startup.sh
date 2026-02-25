#!/bin/bash
# Deploy version: 2026-02-25 - Proper Alembic migrations (no more create_all wipe risk)

echo "=========================================="
echo "Starting UnifiedLayer Backend"
echo "=========================================="

# ── DANGER ZONE ─────────────────────────────────────────────────────────────
# RESET_DATABASE=true drops the entire schema.  Never set this in production.
if [ "$RESET_DATABASE" = "true" ]; then
    echo ""
    echo "WARNING: RESET_DATABASE=true - Wiping database..."
    python3 << 'EOF'
from sqlalchemy import create_engine, text
import os

db_url = os.environ.get("DATABASE_URL")
if db_url:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO PUBLIC"))
        conn.commit()
    print("Database schema reset complete.")
else:
    print("ERROR: DATABASE_URL not set")
EOF
fi
# ────────────────────────────────────────────────────────────────────────────

echo ""
echo "Step 1: Running database migrations..."

# Detect whether this is an existing DB that was built with create_all()
# (it has app tables but no alembic_version row yet).
# If so: fill any tables that were added after the last create_all() run,
# then stamp Alembic at the current head so it doesn't try to replay history.
# On a fresh DB or an already-stamped DB, skip straight to upgrade.
NEEDS_STAMP=$(python3 << 'PYEOF'
import sys
sys.path.insert(0, '/app')
from sqlalchemy import inspect
from backend.database import engine, Base
from backend.models import *  # registers all models with Base.metadata

inspector = inspect(engine)
tables = inspector.get_table_names()
has_app_tables = "users" in tables or "organizations" in tables
has_alembic  = "alembic_version" in tables

if has_app_tables and not has_alembic:
    # Existing DB created before Alembic was wired in.
    # create_all() is safe here: it only adds tables that are missing.
    print("Existing DB without alembic_version — creating any missing tables...", flush=True)
    Base.metadata.create_all(bind=engine)
    print("needs_stamp")
elif not has_app_tables:
    print("Fresh DB — Alembic will create all tables via migrations.")
    print("no_stamp")
else:
    print("Alembic already initialised.")
    print("no_stamp")
PYEOF
)

if echo "$NEEDS_STAMP" | grep -q "needs_stamp"; then
    echo "Stamping Alembic head on existing schema..."
    cd /app && alembic stamp head
    if [ $? -ne 0 ]; then
        echo "ERROR: alembic stamp failed!"
        exit 1
    fi
    echo "Stamp complete."
fi

# Apply any pending migrations (safe no-op if already at head).
cd /app && alembic upgrade head
if [ $? -ne 0 ]; then
    echo "ERROR: Database migration failed!"
    exit 1
fi
echo "Migrations complete!"

echo ""
echo "Step 2: Seeding RBAC roles..."
python3 -m backend.scripts.seed_rbac || {
    echo "WARNING: RBAC seeding had issues"
}

echo ""
echo "Step 3: Creating super admin (first deploy only)..."
export SUPER_ADMIN_PASSWORD="${SUPER_ADMIN_PASSWORD:-Admin123!}"
python3 -m backend.scripts.create_super_admin --env || {
    echo "WARNING: Super admin creation had issues"
}

echo ""
echo "Step 4: Starting uvicorn on port ${PORT:-8000}..."
echo "=========================================="
exec python3 -m uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
