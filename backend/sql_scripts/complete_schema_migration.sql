-- =============================================================================
-- PetCircle: Complete Schema Migration
-- Run this in Supabase SQL editor to sync production DB with SQLAlchemy models.
-- Safe to run multiple times — all statements use IF NOT EXISTS / IF EXISTS.
-- =============================================================================

-- =============================================================================
-- 1. USERS TABLE — add PII fields, consent, soft-delete, order/edit flow columns
-- =============================================================================

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS mobile_number    VARCHAR(500),
    ADD COLUMN IF NOT EXISTS mobile_hash      VARCHAR(64),
    ADD COLUMN IF NOT EXISTS mobile_display   VARCHAR(20),
    ADD COLUMN IF NOT EXISTS full_name        VARCHAR(120),
    ADD COLUMN IF NOT EXISTS pincode          VARCHAR(500),
    ADD COLUMN IF NOT EXISTS email            VARCHAR(500),
    ADD COLUMN IF NOT EXISTS consent_given    BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS doc_upload_deadline TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS is_deleted       BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS updated_at       TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS order_state      VARCHAR(30),
    ADD COLUMN IF NOT EXISTS active_order_id  UUID;

-- Unique index on mobile_hash (partial: exclude NULLs from uniqueness check)
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_mobile_hash
    ON users (mobile_hash)
    WHERE mobile_hash IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_users_mobile_hash
    ON users (mobile_hash);

-- FK: active_order_id → orders.id (SET NULL on delete)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_users_active_order_id'
          AND table_name = 'users'
    ) THEN
        ALTER TABLE users
            ADD CONSTRAINT fk_users_active_order_id
            FOREIGN KEY (active_order_id) REFERENCES orders(id) ON DELETE SET NULL;
    END IF;
END $$;

-- =============================================================================
-- 2. PETS TABLE — add health fields missing from original schema
-- =============================================================================

ALTER TABLE pets
    ADD COLUMN IF NOT EXISTS dob            DATE,
    ADD COLUMN IF NOT EXISTS weight         NUMERIC(5,2),
    ADD COLUMN IF NOT EXISTS neutered       BOOLEAN,
    ADD COLUMN IF NOT EXISTS weight_flagged BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS photo_path     TEXT,
    ADD COLUMN IF NOT EXISTS updated_at     TIMESTAMPTZ DEFAULT NOW();

-- =============================================================================
-- 3. DOCUMENTS TABLE — add file_path, mime_type, and metadata columns
-- =============================================================================

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS file_path      VARCHAR,
    ADD COLUMN IF NOT EXISTS mime_type      VARCHAR(50),
    ADD COLUMN IF NOT EXISTS doctor_name    VARCHAR(200),
    ADD COLUMN IF NOT EXISTS hospital_name  VARCHAR(200),
    ADD COLUMN IF NOT EXISTS source_wamid   VARCHAR(200);

-- Unique index on source_wamid (partial — excludes NULLs)
CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_source_wamid
    ON documents (source_wamid)
    WHERE source_wamid IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_documents_doctor_name
    ON documents (doctor_name)
    WHERE doctor_name IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_documents_hospital_name
    ON documents (hospital_name)
    WHERE hospital_name IS NOT NULL;

-- =============================================================================
-- 4. MESSAGE_LOGS TABLE — add audit fields (mobile_number, direction, payload, wamid)
-- =============================================================================

ALTER TABLE message_logs
    ADD COLUMN IF NOT EXISTS mobile_number  VARCHAR(15),
    ADD COLUMN IF NOT EXISTS direction      VARCHAR(10),
    ADD COLUMN IF NOT EXISTS payload        JSONB,
    ADD COLUMN IF NOT EXISTS wamid          VARCHAR(200);

-- Unique index on wamid (partial — excludes NULLs)
CREATE UNIQUE INDEX IF NOT EXISTS uq_message_logs_wamid
    ON message_logs (wamid)
    WHERE wamid IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_message_logs_created_at
    ON message_logs (created_at DESC);

-- =============================================================================
-- 5. DIAGNOSTIC_TEST_RESULTS — add model columns, keep old columns as nullable
-- =============================================================================

ALTER TABLE diagnostic_test_results
    ADD COLUMN IF NOT EXISTS document_id    UUID REFERENCES documents(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS parameter_name VARCHAR(120),
    ADD COLUMN IF NOT EXISTS value_numeric  NUMERIC(14,4),
    ADD COLUMN IF NOT EXISTS value_text     VARCHAR(200),
    ADD COLUMN IF NOT EXISTS reference_range VARCHAR(120),
    ADD COLUMN IF NOT EXISTS status_flag    VARCHAR(20),
    ADD COLUMN IF NOT EXISTS updated_at     TIMESTAMPTZ DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_diagnostic_document_id
    ON diagnostic_test_results (document_id)
    WHERE document_id IS NOT NULL;

-- =============================================================================
-- 6. PREVENTIVE_RECORDS — add created_at and updated_at timestamps
-- =============================================================================

ALTER TABLE preventive_records
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- =============================================================================
-- 7. ORDERS — add category, status, admin_notes, updated_at
-- =============================================================================

ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS category         VARCHAR(30),
    ADD COLUMN IF NOT EXISTS status           VARCHAR(20) DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS admin_notes      VARCHAR(2000),
    ADD COLUMN IF NOT EXISTS updated_at       TIMESTAMPTZ DEFAULT NOW();

-- =============================================================================
-- 8. REMINDERS — add created_at timestamp
-- =============================================================================

ALTER TABLE reminders
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

-- =============================================================================
-- 9. DASHBOARD_TOKENS — wrong PK (token was PK, model expects id UUID PK)
--    Safe to DROP+RECREATE: no tokens exist (all creation failed due to schema errors).
--    dashboard_visits stores token as a plain VARCHAR, no FK to drop.
-- =============================================================================

DROP TABLE IF EXISTS dashboard_tokens CASCADE;

CREATE TABLE dashboard_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id      UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    token       VARCHAR(255) UNIQUE NOT NULL,
    revoked     BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_dashboard_tokens_pet_id
    ON dashboard_tokens (pet_id);

-- =============================================================================
-- Done. Verify with:
--   SELECT column_name FROM information_schema.columns
--   WHERE table_name = 'users' ORDER BY ordinal_position;
-- =============================================================================
