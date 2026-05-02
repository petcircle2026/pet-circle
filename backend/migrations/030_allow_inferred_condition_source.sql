-- Allow 'inferred' as a valid condition source (GPT-deduced from medications).
-- Previously only 'extraction' and 'manual' were permitted.
ALTER TABLE conditions DROP CONSTRAINT IF EXISTS chk_condition_source;
ALTER TABLE conditions ADD CONSTRAINT chk_condition_source
    CHECK (source IN ('extraction', 'inferred', 'manual'));
