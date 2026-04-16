-- Migration 021: Fix order_recommendations table schema
--
-- The order_recommendations table was created without the columns
-- required by the OrderRecommendation SQLAlchemy model (species, breed,
-- age_range, category, items, used_count).  This migration drops the
-- existing table (which may be empty or structurally incomplete) and
-- recreates it with the full schema.
--
-- Run in Supabase SQL editor.

-- Step 1: Drop the incomplete table (safe — no FK dependents point to it)
DROP TABLE IF EXISTS order_recommendations CASCADE;

-- Step 2: Recreate with full schema
CREATE TABLE order_recommendations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id      UUID REFERENCES pets(id) ON DELETE CASCADE,
    species     VARCHAR(10)  NOT NULL,
    breed       VARCHAR(100),
    age_range   VARCHAR(20),
    category    VARCHAR(30)  NOT NULL,
    items       JSONB        NOT NULL DEFAULT '[]'::jsonb,
    used_count  INTEGER      NOT NULL DEFAULT 0,
    created_at  TIMESTAMP    DEFAULT NOW(),
    updated_at  TIMESTAMP    DEFAULT NOW()
);

-- Step 3: Indexes (match those declared in the SQLAlchemy model)
CREATE INDEX IF NOT EXISTS ix_order_recommendations_species
    ON order_recommendations (species);

CREATE INDEX IF NOT EXISTS ix_order_recommendations_breed
    ON order_recommendations (breed);

CREATE INDEX IF NOT EXISTS ix_order_recommendations_category
    ON order_recommendations (category);

CREATE INDEX IF NOT EXISTS ix_order_recommendations_profile
    ON order_recommendations (species, breed, age_range, category);
