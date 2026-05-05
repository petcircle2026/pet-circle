-- Migration 058: Add is_active flag to diet_items
-- All existing rows are active (no soft-deletes before this migration).
ALTER TABLE diet_items
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS idx_diet_item_pet_active
    ON diet_items(pet_id, is_active);
