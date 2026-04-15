-- Migration: Add missing columns to users table
-- The original users table (all_tables.sql) is missing PII fields,
-- consent, soft-delete, and order/edit flow columns added since initial deployment.
-- All new columns added as nullable or with safe defaults to avoid backfill issues.

-- PII / identity columns
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS mobile_number VARCHAR(500),
    ADD COLUMN IF NOT EXISTS mobile_hash VARCHAR(64),
    ADD COLUMN IF NOT EXISTS mobile_display VARCHAR(20),
    ADD COLUMN IF NOT EXISTS full_name VARCHAR(120),
    ADD COLUMN IF NOT EXISTS pincode VARCHAR(500),
    ADD COLUMN IF NOT EXISTS email VARCHAR(500);

-- Consent + lifecycle
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS consent_given BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS doc_upload_deadline TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Order flow state
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS order_state VARCHAR(30),
    ADD COLUMN IF NOT EXISTS active_order_id UUID;

-- Unique index on mobile_hash for fast lookups (partial: only non-null rows)
CREATE UNIQUE INDEX IF NOT EXISTS users_mobile_hash_unique
    ON users (mobile_hash)
    WHERE mobile_hash IS NOT NULL;

-- Index for admin soft-delete filter
CREATE INDEX IF NOT EXISTS users_is_deleted_idx
    ON users (is_deleted)
    WHERE is_deleted = FALSE;
