#!/bin/bash
# Deploy version: 2026-02-06-v2 - Fixed super admin creation script

echo "=========================================="
echo "Starting UnifiedLayer Backend"
echo "=========================================="

# Check if we should reset the database
if [ "$RESET_DATABASE" = "true" ]; then
    echo ""
    echo "WARNING: RESET_DATABASE=true - Resetting database..."
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
    print("Database schema reset complete!")
else:
    print("ERROR: DATABASE_URL not set")
EOF
fi

echo ""
echo "Step 1: Creating database tables..."
python3 << 'EOF'
import os
import sys
sys.path.insert(0, '/app')

from sqlalchemy import text
from backend.database import engine, Base
# Import all models to register them
from backend.models import *

print("Creating all tables from SQLAlchemy models...")
Base.metadata.create_all(bind=engine)

# Add missing columns if they don't exist (for schema migrations)
print("Checking for missing columns...")
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255)"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider VARCHAR(50)"))
        conn.commit()
        print("Schema migration check complete!")
    except Exception as e:
        print(f"Column check note: {e}")

print("Tables created successfully!")
EOF

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create tables!"
    exit 1
fi

echo ""
echo "Step 2: Seeding RBAC roles..."
python3 -m backend.scripts.seed_rbac || {
    echo "WARNING: RBAC seeding had issues"
}

echo ""
echo "Step 3: Creating/updating super admin..."
export SUPER_ADMIN_PASSWORD="${SUPER_ADMIN_PASSWORD:-Admin123!}"
python3 -m backend.scripts.create_super_admin --env || {
    echo "WARNING: Super admin creation had issues"
}

echo ""
echo "Step 4: Starting uvicorn on port ${PORT:-8000}..."
echo "=========================================="
exec python3 -m uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
