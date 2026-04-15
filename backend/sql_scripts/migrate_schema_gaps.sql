-- Migration: Fix remaining schema gaps found in production logs (2026-04-16).
--
-- Errors addressed:
--   1. column conflict_flags.new_date does not exist
--   2. column diagnostic_test_results.created_at does not exist
--
-- Run once in the Supabase SQL editor after migrate_dashboard_tokens.sql.
-- Safe to re-run: all ALTER TABLE steps use IF NOT EXISTS.
-- =============================================================================

BEGIN;

-- 1. conflict_flags — add new_date column.
--    The model records the conflicting date extracted from a new document.
--    Existing rows get NULL (no historical conflict date to reconstruct).
ALTER TABLE conflict_flags
    ADD COLUMN IF NOT EXISTS new_date DATE;

-- 2. diagnostic_test_results — add created_at column.
--    complete_schema_migration.sql added updated_at but missed created_at.
--    Backfill existing rows with updated_at (best available proxy).
ALTER TABLE diagnostic_test_results
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

UPDATE diagnostic_test_results
SET created_at = COALESCE(updated_at, NOW())
WHERE created_at IS NULL;

COMMIT;

-- Verify:
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'conflict_flags' ORDER BY ordinal_position;
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'diagnostic_test_results' ORDER BY ordinal_position;
