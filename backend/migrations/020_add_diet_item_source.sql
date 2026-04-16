-- Migration 020: Add source tracking to diet_items
-- Distinguishes between document-extracted supplements, manually-added items, and analysis-recommended items

ALTER TABLE diet_items ADD COLUMN source VARCHAR(50) DEFAULT 'manual';

-- Add index on (pet_id, source) for filtering during analysis and recommendations
CREATE INDEX idx_diet_items_pet_source ON diet_items(pet_id, source);

-- Comment explaining the source values
COMMENT ON COLUMN diet_items.source IS
  'Source tracking: document_extracted (from uploaded docs, use only for analysis),
   manual (user-added), analysis_recommended (from diet analysis, safe for quick fixes)';
