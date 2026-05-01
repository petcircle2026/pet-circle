-- Migration 027: Add 'not_started' to preventive_records status constraint
-- Reason: Baseline-seeded records (no history, dates unknown) need a valid status
--         that satisfies the DB constraint without requiring a non-null next_due_date.
--         'upcoming' is no longer valid when next_due_date IS NULL.

-- Drop the old status check constraint and recreate with 'not_started' included.
ALTER TABLE preventive_records
  DROP CONSTRAINT IF EXISTS preventive_records_status_check;

ALTER TABLE preventive_records
  ADD CONSTRAINT preventive_records_status_check
  CHECK (status IN ('up_to_date', 'upcoming', 'overdue', 'cancelled', 'not_started'));
