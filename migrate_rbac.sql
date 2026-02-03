-- RBAC System Migration
-- Run this to create all RBAC tables and update existing tables

-- Create roles table
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    scope VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Create permissions table
CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    CONSTRAINT uq_resource_action UNIQUE (resource, action)
);

-- Create role_permissions junction table
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- Create user_roles junction table
CREATE TABLE IF NOT EXISTS user_roles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    organization_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,
    assigned_by_id INTEGER REFERENCES users(id),
    assigned_at TIMESTAMP DEFAULT NOW() NOT NULL,
    CONSTRAINT uq_user_role_org UNIQUE (user_id, role_id, organization_id)
);

-- Create user_invitations table
CREATE TABLE IF NOT EXISTS user_invitations (
    id SERIAL PRIMARY KEY,
    public_id VARCHAR(36) UNIQUE NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role_id INTEGER NOT NULL REFERENCES roles(id),
    invited_by_id INTEGER NOT NULL REFERENCES users(id),
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    accepted_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS ix_user_roles_user_id ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS ix_user_roles_organization_id ON user_roles(organization_id);
CREATE INDEX IF NOT EXISTS ix_user_invitations_email ON user_invitations(email);
CREATE INDEX IF NOT EXISTS ix_user_invitations_status ON user_invitations(status);
CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_organization_id ON audit_logs(organization_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at);

-- Add subscription fields to organizations table
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS subscription_plan VARCHAR(20) DEFAULT 'starter' NOT NULL;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS max_users INTEGER DEFAULT 3 NOT NULL;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(20) DEFAULT 'active' NOT NULL;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMP;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS billing_email VARCHAR(255);

-- Add invitation-related fields to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE NOT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS invited_by_id INTEGER REFERENCES users(id);
ALTER TABLE users ADD COLUMN IF NOT EXISTS invitation_accepted_at TIMESTAMP;
