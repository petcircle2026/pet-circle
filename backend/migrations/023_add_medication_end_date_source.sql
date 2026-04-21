-- Migration 023: Add end_date_source to condition_medications
-- Tracks whether end_date was captured from an actual document ("record")
-- or assigned as an AI default sentinel ("ai_default").
-- This allows the care plan to suppress display of AI-invented end dates.

ALTER TABLE condition_medications
  ADD COLUMN IF NOT EXISTS end_date_source VARCHAR(20);

-- Back-fill: any existing row where end_date = '2099-12-31' is an AI default.
UPDATE condition_medications
   SET end_date_source = 'ai_default'
 WHERE end_date = '2099-12-31';
