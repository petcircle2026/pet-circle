-- Migration 057: Add item_type to custom_preventive_items
--
-- Stores the preventive category ('vaccine', 'deworming', 'tick_flea', 'other')
-- set at extraction time so cadence builders don't rely on fragile keyword matching
-- against raw item names like "ARV" or "10 in 1".
--
-- NULL = legacy row; cadence builder falls back to keyword matching for these.

ALTER TABLE custom_preventive_items
ADD COLUMN IF NOT EXISTS item_type VARCHAR(20) DEFAULT NULL;

COMMENT ON COLUMN custom_preventive_items.item_type IS
  'Preventive category: vaccine | deworming | tick_flea | other. NULL = unknown (keyword fallback).';
