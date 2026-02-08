#!/bin/bash
set -e

echo "Running database migrations..."
cd /app
python -c "
from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Fix for Railway's postgres:// URL
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Add missing OAuth columns
        conn.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255)'))
        conn.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider VARCHAR(50)'))
        conn.commit()
        print('Database columns checked/added successfully')
else:
    print('WARNING: DATABASE_URL not set')
"

echo "Starting server..."
exec uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --workers 4
