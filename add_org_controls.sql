-- Add organization control flags for super admin
-- can_sync_data: Controls whether org can run pipelines (soft warning)
-- is_active: Already exists, controls complete access (hard shutdown)

ALTER TABLE organizations
ADD COLUMN IF NOT EXISTS can_sync_data BOOLEAN NOT NULL DEFAULT TRUE;

-- Add comments
COMMENT ON COLUMN organizations.is_active IS 'Hard shutdown: When false, organization is completely locked out (no login, no access)';
COMMENT ON COLUMN organizations.can_sync_data IS 'Soft warning: When false, users can login but cannot run pipelines/sync data';
