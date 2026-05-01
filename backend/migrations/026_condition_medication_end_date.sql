-- Migration 026: Add medication_end_date to conditions, remove status from condition_medications
-- Reason: Denormalize max medication end_date on condition for query performance;
--         Remove misleading status column from medications (status computed at runtime)

-- Add medication_end_date to conditions table
ALTER TABLE conditions ADD COLUMN IF NOT EXISTS medication_end_date DATE;
CREATE INDEX IF NOT EXISTS idx_conditions_medication_end ON conditions(medication_end_date);

-- Remove status column from condition_medications (it's always 'active', misleading)
ALTER TABLE condition_medications DROP COLUMN IF EXISTS status;

-- (Optional) Backfill medication_end_date on conditions from existing medications
-- This is a one-time operation; future extractions will set it at insert time.
UPDATE conditions c
SET medication_end_date = (
    SELECT MAX(end_date) FROM condition_medications
    WHERE condition_id = c.id AND end_date IS NOT NULL
)
WHERE medication_end_date IS NULL;
