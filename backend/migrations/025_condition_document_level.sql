-- Migration 025: Document-level conditions + aggregated_conditions table
--
-- Key changes:
-- 1. Create aggregated_conditions table (one row per condition family per pet)
-- 2. Drop (pet_id, name) unique constraint from conditions (one row per doc now)
-- 3. Add 'recurrent' to condition_type CHECK constraint
-- 4. Add condition_family_id + recurrence_watch columns to conditions

-- ─── 1. Create aggregated_conditions table ────────────────────────────────────
CREATE TABLE IF NOT EXISTS aggregated_conditions (
    id                   UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id               UUID          NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    name                 VARCHAR(200)  NOT NULL,
    condition_type       VARCHAR(20)   NOT NULL DEFAULT 'episodic'
                             CHECK (condition_type IN ('chronic', 'episodic', 'recurrent')),
    condition_status     VARCHAR(20),
    episode_dates        JSONB         NOT NULL DEFAULT '[]',
    diagnosed_at         DATE,
    last_record_date     DATE,
    medication_end_date  DATE,
    medications          JSONB         NOT NULL DEFAULT '[]',
    monitoring           JSONB         NOT NULL DEFAULT '[]',
    soft_resolution      BOOLEAN       NOT NULL DEFAULT FALSE,
    recurrence_watch     BOOLEAN       NOT NULL DEFAULT FALSE,
    canonical_condition_id UUID,
    created_at           TIMESTAMP     NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMP     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_aggregated_conditions_pet
    ON aggregated_conditions(pet_id);

-- ─── 2. Drop the (pet_id, name) unique constraint from conditions ─────────────
ALTER TABLE conditions DROP CONSTRAINT IF EXISTS uq_conditions_pet_name;

-- ─── 3. Update condition_type CHECK to include 'recurrent' ───────────────────
ALTER TABLE conditions DROP CONSTRAINT IF EXISTS conditions_condition_type_check;
ALTER TABLE conditions ADD CONSTRAINT conditions_condition_type_check
    CHECK (condition_type IN ('chronic', 'episodic', 'recurrent', 'resolved'));

-- ─── 4. Add new columns to conditions ────────────────────────────────────────
ALTER TABLE conditions
    ADD COLUMN IF NOT EXISTS condition_family_id UUID
        REFERENCES aggregated_conditions(id) ON DELETE SET NULL;

ALTER TABLE conditions
    ADD COLUMN IF NOT EXISTS recurrence_watch BOOLEAN NOT NULL DEFAULT FALSE;

-- ─── 5. Add FK from aggregated_conditions.canonical_condition_id → conditions ─
ALTER TABLE aggregated_conditions
    ADD CONSTRAINT fk_aggregated_conditions_canonical
    FOREIGN KEY (canonical_condition_id)
    REFERENCES conditions(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_conditions_family_id
    ON conditions(condition_family_id);
