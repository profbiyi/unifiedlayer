#!/bin/bash
# Database backup script

set -e

# Configuration
BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_NAME=${POSTGRES_DB:-dataplatform}
DB_USER=${POSTGRES_USER:-dataplatform}
DB_HOST=${POSTGRES_HOST:-localhost}
S3_BUCKET=${BACKUP_S3_BUCKET:-""}

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Backup filename
BACKUP_FILE="${BACKUP_DIR}/backup_${DB_NAME}_${TIMESTAMP}.sql.gz"

echo "Starting backup of database: ${DB_NAME}"

# Create backup
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
  -h "${DB_HOST}" \
  -U "${DB_USER}" \
  -d "${DB_NAME}" \
  --verbose \
  | gzip > "${BACKUP_FILE}"

echo "Backup created: ${BACKUP_FILE}"

# Upload to S3 if configured
if [ -n "${S3_BUCKET}" ]; then
  echo "Uploading backup to S3: ${S3_BUCKET}"
  aws s3 cp "${BACKUP_FILE}" "s3://${S3_BUCKET}/database-backups/"
  echo "Upload complete"
fi

# Clean up old backups (keep last 7 days)
find "${BACKUP_DIR}" -name "backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed successfully"
