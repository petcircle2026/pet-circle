-- Migration: Fix message_logs table schema
-- The original table used user_id/pet_id/content/status columns.
-- The current model (message_log.py) expects mobile_number, direction, payload, wamid.
-- This migration adds the missing columns WITHOUT dropping old ones (safe, non-destructive).

-- Add missing columns
ALTER TABLE message_logs
    ADD COLUMN IF NOT EXISTS mobile_number VARCHAR(15),
    ADD COLUMN IF NOT EXISTS direction VARCHAR(10),
    ADD COLUMN IF NOT EXISTS payload JSONB,
    ADD COLUMN IF NOT EXISTS wamid VARCHAR(200);

-- Add unique index on wamid for deduplication (only for non-NULL values)
CREATE UNIQUE INDEX IF NOT EXISTS message_logs_wamid_unique
    ON message_logs (wamid)
    WHERE wamid IS NOT NULL;

-- Add index on created_at for admin panel ordering (if not already present)
CREATE INDEX IF NOT EXISTS message_logs_created_at_idx
    ON message_logs (created_at DESC);
