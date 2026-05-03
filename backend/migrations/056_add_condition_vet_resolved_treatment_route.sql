-- Migration 056: Add vet_resolved, treatment_route to conditions;
--               add latest_episode_condition_id to aggregated_conditions.
--
-- vet_resolved: manual vet override — marks a condition as definitively resolved
--               regardless of medication/date heuristics.
-- treatment_route: how the condition is being treated (e.g. 'topical', 'oral', 'systemic').
-- latest_episode_condition_id: FK pointing to the most-recently-diagnosed conditions row
--               in this family; used in the health_conditions_v2 precompute JOIN.

-- ─── 1. conditions table ─────────────────────────────────────────────────────

ALTER TABLE conditions
    ADD COLUMN IF NOT EXISTS vet_resolved      BOOLEAN      NOT NULL DEFAULT FALSE;

ALTER TABLE conditions
    ADD COLUMN IF NOT EXISTS treatment_route   VARCHAR(100);

-- ─── 2. aggregated_conditions table ──────────────────────────────────────────

ALTER TABLE aggregated_conditions
    ADD COLUMN IF NOT EXISTS latest_episode_condition_id UUID
        REFERENCES conditions(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_aggregated_conditions_latest_episode
    ON aggregated_conditions(latest_episode_condition_id);
