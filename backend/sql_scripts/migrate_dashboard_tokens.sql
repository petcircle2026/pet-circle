-- Migration: Bring dashboard_tokens in line with the SQLAlchemy model.
--
-- The original all_tables.sql created dashboard_tokens with `token` as the
-- primary key and no id / revoked / expires_at columns.  The model and all
-- service code expect the richer schema defined in complete_schema_migration.sql.
-- This script performs the migration non-destructively (no DROP TABLE).
--
-- Run once in the Supabase SQL editor.
-- Safe to re-run: all steps are guarded with IF NOT EXISTS / IF EXISTS.
-- =============================================================================

BEGIN;

-- 1. Add id column (UUID, auto-generated) if it doesn't already exist.
ALTER TABLE dashboard_tokens
    ADD COLUMN IF NOT EXISTS id UUID DEFAULT gen_random_uuid();

-- 2. Populate id for any rows that were inserted before this migration.
UPDATE dashboard_tokens SET id = gen_random_uuid() WHERE id IS NULL;

-- 3. Drop the old primary key on token (constraint name may vary — use the
--    catalog to find it first; Supabase typically names it dashboard_tokens_pkey).
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'dashboard_tokens'::regclass
          AND contype = 'p'
          AND conname = 'dashboard_tokens_pkey'
    ) THEN
        -- Only drop-and-recreate if 'token' is still the PK column.
        IF EXISTS (
            SELECT 1 FROM pg_attribute a
            JOIN pg_constraint c ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
            WHERE c.conrelid = 'dashboard_tokens'::regclass
              AND c.contype = 'p'
              AND a.attname = 'token'
        ) THEN
            ALTER TABLE dashboard_tokens DROP CONSTRAINT dashboard_tokens_pkey;
        END IF;
    END IF;
END;
$$;

-- 4. Make id NOT NULL and promote it to primary key.
ALTER TABLE dashboard_tokens ALTER COLUMN id SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'dashboard_tokens'::regclass AND contype = 'p'
    ) THEN
        ALTER TABLE dashboard_tokens ADD PRIMARY KEY (id);
    END IF;
END;
$$;

-- 5. Ensure token has a UNIQUE constraint (was implicit as PK; now explicit).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'dashboard_tokens'::regclass
          AND contype = 'u'
          AND conname = 'dashboard_tokens_token_key'
    ) THEN
        ALTER TABLE dashboard_tokens ADD CONSTRAINT dashboard_tokens_token_key UNIQUE (token);
    END IF;
END;
$$;

-- 6. Add revoked column.
ALTER TABLE dashboard_tokens
    ADD COLUMN IF NOT EXISTS revoked BOOLEAN NOT NULL DEFAULT FALSE;

-- 7. Add expires_at column (nullable initially so existing rows are not rejected).
ALTER TABLE dashboard_tokens
    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

-- 8. Give existing rows a generous expiry so they remain usable after migration.
UPDATE dashboard_tokens
SET expires_at = NOW() + INTERVAL '365 days'
WHERE expires_at IS NULL;

-- 9. Ensure the pet_id index exists.
CREATE INDEX IF NOT EXISTS ix_dashboard_tokens_pet_id ON dashboard_tokens (pet_id);

COMMIT;

-- Verify:
-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_name = 'dashboard_tokens' ORDER BY ordinal_position;
