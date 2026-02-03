#!/bin/bash
# Bootstrap Script for Data Platform
# This script sets up the initial super admin and RBAC system

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo ""
echo "=========================================="
echo "🚀 Data Platform Bootstrap Script"
echo "=========================================="
echo ""

# Check if database is running
echo "📋 Step 1: Checking database connection..."
if docker ps | grep -q data-platform-db; then
    echo "   ✅ Database container is running"
else
    echo "   ❌ Database container is not running!"
    echo "   Please start the database first:"
    echo "   cd docker && docker-compose up -d postgres"
    exit 1
fi

# Check if backend is accessible
echo ""
echo "📋 Step 2: Checking backend service..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "   ✅ Backend is running"
else
    echo "   ⚠️  Backend is not running"
    echo "   You can run: cd docker && docker-compose up -d backend"
    echo "   Or run manually: python -m uvicorn backend.api.main:app"
fi

# Run database migrations
echo ""
echo "📋 Step 3: Running database migrations..."
cd "$PROJECT_ROOT"
if docker exec data-platform-db psql -U dataplatform -d dataplatform -c "SELECT 1" > /dev/null 2>&1; then
    echo "   ✅ Database is accessible"
else
    echo "   ❌ Cannot connect to database"
    exit 1
fi

# Seed RBAC roles
echo ""
echo "📋 Step 4: Seeding RBAC roles..."
if python -m backend.scripts.seed_rbac; then
    echo "   ✅ RBAC roles seeded successfully"
else
    echo "   ⚠️  RBAC seeding failed or already done"
fi

# Create super admin
echo ""
echo "📋 Step 5: Creating Super Admin user..."
echo ""
echo "You can either:"
echo "  1. Enter credentials interactively (recommended)"
echo "  2. Use environment variables"
echo ""
read -p "Choose mode [1/2]: " mode

if [ "$mode" = "2" ]; then
    echo ""
    echo "Please set these environment variables first:"
    echo "  export SUPER_ADMIN_EMAIL='admin@example.com'"
    echo "  export SUPER_ADMIN_USERNAME='superadmin'"
    echo "  export SUPER_ADMIN_PASSWORD='YourPassword123'"
    echo "  export SUPER_ADMIN_FULLNAME='Admin Name'"
    echo ""
    echo "Then run this script again."
    exit 0
else
    python -m backend.scripts.create_super_admin
fi

echo ""
echo "=========================================="
echo "✅ Bootstrap Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Login at: http://localhost:3000/login"
echo "  2. Use the credentials you just created"
echo "  3. Access admin dashboard: http://localhost:3000/admin"
echo "  4. Create your first organization"
echo ""
echo "📖 For detailed instructions, see: ONBOARDING.md"
echo ""
