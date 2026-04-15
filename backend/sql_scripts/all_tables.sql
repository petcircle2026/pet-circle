-- ============================================================================
-- PETCIRCLE COMPLETE SCHEMA MIGRATION
-- ============================================================================
--
-- Creates the entire PetCircle database from scratch with all active tables.
-- This is a consolidated migration combining 59+ individual migrations into
-- a single, dependency-ordered schema setup.
--
-- Table order: Core → Pets → Documents → Preventive → Reminders → Conditions →
--             Health → Nutrition → Hygiene → Orders → Cart → Nudges → Engagement
--
-- ARCHIVE TABLES: None (all active tables only)
-- TOTAL TABLES: 33 active tables
--

BEGIN;

-- ============================================================================
-- 1. CORE USER TABLES
-- ============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    onboarding_state VARCHAR,
    onboarding_data JSONB,
    onboarding_completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    dashboard_link_pending BOOLEAN NOT NULL DEFAULT FALSE,
    active_reminder_id UUID,
    delivery_address TEXT,
    payment_method_pref VARCHAR(10),
    saved_upi_id VARCHAR(500),
    edit_state VARCHAR(30),
    edit_data JSONB
);

CREATE INDEX idx_users_onboarding_completed
    ON users (onboarding_completed_at)
    WHERE onboarding_completed_at IS NOT NULL;

CREATE TABLE shown_fun_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fact_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, fact_hash)
);

CREATE INDEX idx_shown_fun_facts_user_id ON shown_fun_facts (user_id);

-- ============================================================================
-- 2. PET TABLES
-- ============================================================================

CREATE TABLE pets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    species VARCHAR NOT NULL,
    breed VARCHAR,
    gender VARCHAR,
    age_text VARCHAR(50),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pets_user_id ON pets (user_id);

CREATE TABLE pet_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    category VARCHAR(30) NOT NULL,
    preference_type VARCHAR(20) NOT NULL DEFAULT 'custom',
    item_name VARCHAR(500) NOT NULL,
    used_count INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_pet_preferences_pet_category ON pet_preferences (pet_id, category);
CREATE INDEX ix_pet_preferences_preference_type ON pet_preferences (preference_type);

-- ============================================================================
-- 3. DOCUMENT TABLES
-- ============================================================================

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    document_name VARCHAR NOT NULL,
    document_category VARCHAR NOT NULL,
    extraction_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    storage_backend VARCHAR(20) NOT NULL DEFAULT 'supabase',
    rejection_reason VARCHAR(200),
    retry_count INTEGER NOT NULL DEFAULT 0,
    content_hash VARCHAR(64),
    extraction_confidence FLOAT,
    diagnostic_summary TEXT,
    non_diet_recommendations JSONB,
    event_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_extraction_status CHECK (extraction_status IN ('pending','success','partially_extracted','failed','rejected')),
    CONSTRAINT chk_storage_backend CHECK (storage_backend IN ('gcp','supabase'))
);

CREATE INDEX idx_documents_pet_extraction ON documents (pet_id, extraction_status);
CREATE INDEX idx_documents_retry_eligible ON documents (retry_count) WHERE extraction_status = 'failed';
CREATE INDEX idx_documents_content_hash ON documents (content_hash, pet_id) WHERE content_hash IS NOT NULL;
CREATE INDEX ix_documents_storage_backend ON documents (storage_backend);

-- ============================================================================
-- 4. PREVENTIVE MASTER & RECORDS
-- ============================================================================

CREATE TABLE preventive_master (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_name VARCHAR(120) NOT NULL,
    category VARCHAR(20) NOT NULL DEFAULT 'complete',
    circle VARCHAR(20) NOT NULL,
    species VARCHAR(10) NOT NULL,
    recurrence_days INTEGER NOT NULL,
    medicine_dependent BOOLEAN DEFAULT FALSE,
    reminder_before_days INTEGER DEFAULT 7,
    overdue_after_days INTEGER DEFAULT 7,
    is_core BOOLEAN NOT NULL DEFAULT FALSE,
    is_mandatory BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_preventive_category CHECK (category IN ('essential','complete')),
    CONSTRAINT chk_preventive_circle CHECK (circle IN ('health','nutrition','hygiene')),
    CONSTRAINT chk_preventive_species CHECK (species IN ('dog','cat','both')),
    UNIQUE (item_name, species)
);

CREATE TABLE custom_preventive_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    item_name VARCHAR(120) NOT NULL,
    category VARCHAR(20) NOT NULL DEFAULT 'complete',
    circle VARCHAR(20) NOT NULL DEFAULT 'health',
    species VARCHAR(10) NOT NULL,
    recurrence_days INTEGER NOT NULL,
    medicine_dependent BOOLEAN DEFAULT FALSE,
    reminder_before_days INTEGER NOT NULL DEFAULT 7,
    overdue_after_days INTEGER NOT NULL DEFAULT 7,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_custom_category CHECK (category IN ('essential','complete')),
    CONSTRAINT chk_custom_circle CHECK (circle IN ('health','nutrition','hygiene')),
    CONSTRAINT chk_custom_species CHECK (species IN ('dog','cat','both')),
    UNIQUE (user_id, item_name, species)
);

CREATE INDEX ix_custom_preventive_items_user_id ON custom_preventive_items (user_id);

CREATE TABLE preventive_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    preventive_master_id UUID REFERENCES preventive_master(id),
    custom_preventive_item_id UUID REFERENCES custom_preventive_items(id),
    last_done_date DATE,
    next_due_date DATE,
    status VARCHAR(20),
    custom_recurrence_days INTEGER,
    medicine_name VARCHAR(200),
    vaccination_metadata JSONB,
    CONSTRAINT chk_preventive_one_source CHECK (
        (preventive_master_id IS NOT NULL AND custom_preventive_item_id IS NULL) OR
        (preventive_master_id IS NULL AND custom_preventive_item_id IS NOT NULL)
    ),
    UNIQUE (pet_id, custom_preventive_item_id, last_done_date)
);

CREATE INDEX idx_preventive_records_pet_status ON preventive_records (pet_id, status);
CREATE INDEX idx_preventive_records_pet_next_due ON preventive_records (pet_id, next_due_date ASC);

-- ============================================================================
-- 5. REMINDER & CONFLICT TABLES
-- ============================================================================

CREATE TABLE reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    preventive_record_id UUID REFERENCES preventive_records(id),
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    next_due_date DATE,
    status VARCHAR(20),
    stage VARCHAR(20) NOT NULL DEFAULT 'due',
    ignore_count INTEGER NOT NULL DEFAULT 0,
    monthly_fallback BOOLEAN NOT NULL DEFAULT FALSE,
    last_ignored_at TIMESTAMPTZ,
    source_type VARCHAR(30),
    source_id UUID,
    item_desc VARCHAR(300),
    sub_type VARCHAR(30),
    template_name VARCHAR(100),
    template_params JSONB,
    message_body TEXT,
    sent_at TIMESTAMPTZ,
    CONSTRAINT chk_reminder_stage CHECK (stage IN ('t7','due','d3','overdue_insight')),
    UNIQUE (preventive_record_id, next_due_date, stage)
);

CREATE INDEX idx_reminders_record_status ON reminders (preventive_record_id, status);
CREATE INDEX idx_reminders_stage ON reminders (stage, status);
CREATE INDEX idx_reminders_monthly_fallback ON reminders (monthly_fallback, status) WHERE monthly_fallback = TRUE;
CREATE INDEX idx_reminders_pet_id ON reminders (pet_id, status, sent_at);

CREATE TABLE conflict_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    preventive_record_id UUID NOT NULL REFERENCES preventive_records(id),
    status VARCHAR(20),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_conflict_flags_record_status ON conflict_flags (preventive_record_id, status);

-- ============================================================================
-- 6. CONDITION TABLES
-- ============================================================================

CREATE TABLE conditions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    name VARCHAR(200) NOT NULL,
    diagnosis VARCHAR(500),
    condition_type VARCHAR(20) NOT NULL DEFAULT 'chronic',
    diagnosed_at DATE,
    notes VARCHAR(1000),
    source VARCHAR(20) NOT NULL DEFAULT 'extraction',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    icon VARCHAR(10),
    managed_by VARCHAR(200),
    condition_status VARCHAR(20),
    episode_dates JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_condition_type CHECK (condition_type IN ('chronic','episodic','resolved')),
    CONSTRAINT chk_condition_source CHECK (source IN ('extraction','manual')),
    UNIQUE (pet_id, name)
);

CREATE INDEX idx_conditions_pet_id ON conditions (pet_id);
CREATE INDEX idx_conditions_document_id ON conditions (document_id);
CREATE INDEX idx_conditions_pet_active ON conditions (pet_id, is_active);

CREATE TABLE condition_medications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    condition_id UUID NOT NULL REFERENCES conditions(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    dose VARCHAR(100),
    frequency VARCHAR(100),
    route VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    started_at DATE,
    notes VARCHAR(500),
    refill_due_date DATE,
    price VARCHAR(20),
    end_date DATE,
    item_type VARCHAR(20) NOT NULL DEFAULT 'medicine',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_medication_status CHECK (status IN ('active','discontinued'))
);

CREATE INDEX idx_condition_medications_condition_id ON condition_medications (condition_id);

CREATE TABLE condition_monitoring (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    condition_id UUID NOT NULL REFERENCES conditions(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    frequency VARCHAR(100),
    next_due_date DATE,
    last_done_date DATE,
    result_summary VARCHAR(200),
    recheck_due_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_condition_monitoring_condition_id ON condition_monitoring (condition_id);

CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'veterinarian',
    name VARCHAR(200) NOT NULL,
    clinic_name VARCHAR(200),
    phone VARCHAR(30),
    email VARCHAR(200),
    address VARCHAR(500),
    source VARCHAR(20) NOT NULL DEFAULT 'extraction',
    source_document_name VARCHAR(200),
    source_document_category VARCHAR(30),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_contact_role CHECK (role IN ('veterinarian','groomer','trainer','specialist','other')),
    CONSTRAINT chk_contact_source CHECK (source IN ('extraction','manual')),
    UNIQUE (pet_id, name, role)
);

CREATE INDEX idx_contacts_pet_id ON contacts (pet_id);
CREATE INDEX idx_contacts_document_id ON contacts (document_id);

CREATE TABLE diagnostic_test_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id UUID NOT NULL REFERENCES pets(id),
    observed_at DATE,
    test_type VARCHAR(20),
    test_name VARCHAR(200),
    value VARCHAR(100),
    unit VARCHAR(50),
    normal_range VARCHAR(100),
    CONSTRAINT chk_test_type CHECK (test_type IN ('blood','urine','vital'))
);

CREATE INDEX idx_diagnostic_test_results_pet ON diagnostic_test_results (pet_id);

-- ============================================================================
-- 7. HEALTH & WEIGHT TABLES
-- ============================================================================

CREATE TABLE weight_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    weight DECIMAL(5,2) NOT NULL,
    recorded_at DATE NOT NULL,
    note VARCHAR(255),
    bcs SMALLINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_bcs CHECK (bcs IS NULL OR (bcs >= 1 AND bcs <= 9))
);

CREATE INDEX idx_weight_history_pet_id ON weight_history (pet_id);

CREATE TABLE ideal_weight_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    species VARCHAR(10) NOT NULL,
    breed_normalized VARCHAR(100) NOT NULL,
    gender VARCHAR(10) NOT NULL,
    age_category VARCHAR(20) NOT NULL,
    min_weight DECIMAL(5,2) NOT NULL,
    max_weight DECIMAL(5,2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (species, breed_normalized, gender, age_category)
);

CREATE TABLE pet_ai_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    insight_type VARCHAR(50) NOT NULL,
    content_json JSONB NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (pet_id, insight_type)
);

CREATE INDEX ix_pet_ai_insights_pet_id ON pet_ai_insights (pet_id);
CREATE INDEX idx_pet_ai_insights_pet_type ON pet_ai_insights (pet_id, insight_type, generated_at);

CREATE TABLE pet_life_stage_traits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    life_stage VARCHAR(20) NOT NULL,
    breed_size VARCHAR(20) NOT NULL,
    traits JSONB NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (pet_id, life_stage)
);

CREATE INDEX ix_pet_life_stage_traits_pet_id ON pet_life_stage_traits (pet_id);

-- ============================================================================
-- 8. NUTRITION & DIET TABLES
-- ============================================================================

CREATE TABLE diet_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    type VARCHAR(20) NOT NULL,
    icon VARCHAR(10),
    label VARCHAR(200) NOT NULL,
    detail VARCHAR(200),
    brand VARCHAR(200),
    pack_size_g INTEGER,
    daily_portion_g INTEGER,
    units_in_pack INTEGER,
    doses_per_day INTEGER,
    last_purchase_date DATE,
    reminder_order_at_o21 BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (pet_id, label, type)
);

CREATE INDEX idx_diet_items_pet_id ON diet_items (pet_id);

CREATE TABLE nutrition_target_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    species VARCHAR(10) NOT NULL,
    breed_normalized VARCHAR(100) NOT NULL,
    age_category VARCHAR(20) NOT NULL,
    targets_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (species, breed_normalized, age_category)
);

CREATE INDEX idx_nutrition_target_lookup ON nutrition_target_cache (species, breed_normalized, age_category);

CREATE TABLE food_nutrition_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    food_label_normalized VARCHAR(200) NOT NULL,
    food_type VARCHAR(20) NOT NULL,
    nutrition_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (food_label_normalized, food_type)
);

CREATE INDEX idx_food_nutrition_lookup ON food_nutrition_cache (food_label_normalized, food_type);

-- ============================================================================
-- 9. HYGIENE & GROOMING TABLES
-- ============================================================================

CREATE TABLE hygiene_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    item_id VARCHAR(50) NOT NULL,
    freq INTEGER NOT NULL DEFAULT 1,
    unit VARCHAR(10) NOT NULL DEFAULT 'month',
    reminder BOOLEAN NOT NULL DEFAULT FALSE,
    last_done VARCHAR(20),
    name VARCHAR(100),
    icon VARCHAR(10) DEFAULT '🧹',
    category VARCHAR(20) DEFAULT 'daily',
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (pet_id, item_id)
);

CREATE INDEX idx_hygiene_preferences_pet_id ON hygiene_preferences (pet_id);

CREATE TABLE hygiene_tip_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    species VARCHAR(10) NOT NULL,
    breed_normalized VARCHAR(100) NOT NULL,
    item_id VARCHAR(50) NOT NULL,
    tip VARCHAR(300) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (species, breed_normalized, item_id)
);

CREATE INDEX idx_hygiene_tip_cache_lookup ON hygiene_tip_cache (species, breed_normalized);

-- ============================================================================
-- 10. CART & PRODUCT TABLES
-- ============================================================================

CREATE TABLE cart_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    product_id VARCHAR(10) NOT NULL,
    icon VARCHAR(10),
    name VARCHAR(200) NOT NULL,
    sub VARCHAR(200),
    price INTEGER NOT NULL,
    tag VARCHAR(30),
    tag_color VARCHAR(10),
    in_cart BOOLEAN NOT NULL DEFAULT FALSE,
    quantity INTEGER NOT NULL DEFAULT 1,
    cart_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (pet_id, product_id)
);

CREATE INDEX idx_cart_items_pet_id ON cart_items (pet_id);

CREATE TABLE product_food (
    sku_id VARCHAR(10) PRIMARY KEY,
    brand_id VARCHAR(10) NOT NULL,
    brand_name VARCHAR(100) NOT NULL,
    product_line VARCHAR(200) NOT NULL,
    life_stage VARCHAR(20) NOT NULL,
    breed_size VARCHAR(20) NOT NULL,
    pack_size_kg NUMERIC(5,1) NOT NULL,
    mrp INTEGER NOT NULL,
    discounted_price INTEGER NOT NULL,
    condition_tags TEXT,
    breed_tags TEXT,
    vet_diet_flag BOOLEAN NOT NULL DEFAULT FALSE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    popularity_rank INTEGER NOT NULL,
    monthly_units_sold INTEGER,
    price_per_kg INTEGER,
    in_stock BOOLEAN NOT NULL DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_product_food_brand_id ON product_food (brand_id);
CREATE INDEX idx_product_food_life_stage_breed ON product_food (life_stage, breed_size);
CREATE INDEX idx_product_food_condition_tags ON product_food (condition_tags);

CREATE TABLE product_supplement (
    sku_id VARCHAR(10) PRIMARY KEY,
    brand_id VARCHAR(10) NOT NULL,
    brand_name VARCHAR(100) NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    type VARCHAR(50) NOT NULL,
    form VARCHAR(30) NOT NULL,
    pack_size VARCHAR(50) NOT NULL,
    mrp INTEGER NOT NULL,
    discounted_price INTEGER NOT NULL,
    key_ingredients TEXT,
    condition_tags TEXT,
    life_stage_tags TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    popularity_rank INTEGER NOT NULL,
    monthly_units INTEGER,
    price_per_unit INTEGER,
    in_stock BOOLEAN NOT NULL DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_product_supplement_brand_id ON product_supplement (brand_id);
CREATE INDEX idx_product_supplement_type ON product_supplement (type);

CREATE TABLE product_medicines (
    sku_id VARCHAR(10) PRIMARY KEY,
    brand_id VARCHAR(10) NOT NULL,
    brand_name VARCHAR(100) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    form VARCHAR(50) NOT NULL,
    pack_size VARCHAR(100) NOT NULL,
    mrp_paise INTEGER NOT NULL,
    discounted_paise INTEGER NOT NULL,
    key_ingredients TEXT,
    condition_tags TEXT,
    life_stage_tags TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    popularity_rank INTEGER,
    monthly_units_sold INTEGER,
    price_per_unit_paise INTEGER,
    in_stock BOOLEAN NOT NULL DEFAULT TRUE,
    dosage TEXT,
    repeat_frequency VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_product_medicines_brand_id ON product_medicines (brand_id);
CREATE INDEX idx_product_medicines_type ON product_medicines (type);
CREATE INDEX idx_product_medicines_condition_tags ON product_medicines (condition_tags);
CREATE INDEX idx_product_medicines_life_stage_tags ON product_medicines (life_stage_tags);

-- ============================================================================
-- 11. ORDER TABLES
-- ============================================================================

CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    pet_id UUID REFERENCES pets(id),
    items_description TEXT,
    razorpay_order_id VARCHAR(100),
    razorpay_payment_id VARCHAR(100),
    payment_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_orders_razorpay_order_id ON orders (razorpay_order_id)
    WHERE razorpay_order_id IS NOT NULL;

CREATE TABLE order_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id UUID REFERENCES pets(id),
    recommendation_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE user_checkout_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    payment_method VARCHAR(50),
    delivery_pincode VARCHAR(10),
    preferences_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 12. DASHBOARD & ADMIN TABLES
-- ============================================================================

CREATE TABLE dashboard_tokens (
    token VARCHAR(200) PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_dashboard_tokens_token ON dashboard_tokens (token);

CREATE TABLE dashboard_visits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    token VARCHAR(200) NOT NULL,
    visited_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_dashboard_visits_user_visited ON dashboard_visits (user_id, visited_at DESC);
CREATE INDEX idx_dashboard_visits_pet_visited ON dashboard_visits (pet_id, visited_at DESC);

CREATE TABLE deferred_care_plan_pending (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    reason VARCHAR(64) NOT NULL DEFAULT 'pending_extractions',
    is_cleared BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    cleared_at TIMESTAMPTZ
);

CREATE INDEX ix_deferred_care_plan_pending_pet ON deferred_care_plan_pending (pet_id);
CREATE INDEX ix_deferred_care_plan_pending_user ON deferred_care_plan_pending (user_id);
CREATE INDEX ix_deferred_care_plan_pending_uncleared ON deferred_care_plan_pending (is_cleared, pet_id);
CREATE UNIQUE INDEX uq_deferred_care_plan_pending_pet_active ON deferred_care_plan_pending (pet_id) WHERE is_cleared = FALSE;

-- ============================================================================
-- 13. NUDGE & ENGAGEMENT TABLES
-- ============================================================================

CREATE TABLE nudges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    category VARCHAR(30) NOT NULL,
    priority VARCHAR(10) NOT NULL,
    icon VARCHAR(10),
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    mandatory BOOLEAN NOT NULL DEFAULT FALSE,
    orderable BOOLEAN NOT NULL DEFAULT FALSE,
    price VARCHAR(20),
    order_type VARCHAR(30),
    cart_item_id VARCHAR(10),
    dismissed BOOLEAN NOT NULL DEFAULT FALSE,
    source VARCHAR(20) DEFAULT 'record',
    wa_status VARCHAR(20),
    wa_sent_at TIMESTAMPTZ,
    wa_message_id VARCHAR(100),
    trigger_type VARCHAR(20) DEFAULT 'cron',
    expires_at DATE,
    acted_on BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_nudge_category CHECK (category IN ('vaccine','deworming','flea','condition','nutrition','grooming','checkup'))
);

CREATE INDEX idx_nudges_pet_id ON nudges (pet_id);
CREATE INDEX idx_nudges_pet_dismissed ON nudges (pet_id, dismissed);
CREATE INDEX idx_nudges_pet_created ON nudges (pet_id, created_at DESC);

CREATE TABLE nudge_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(100) NOT NULL UNIQUE,
    value VARCHAR(200) NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE nudge_delivery_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nudge_id UUID REFERENCES nudges(id) ON DELETE CASCADE,
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    wa_status VARCHAR(20),
    nudge_level INTEGER,
    template_name VARCHAR(100),
    template_params JSONB,
    message_body TEXT,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_nudge_delivery_log_user_sent ON nudge_delivery_log (user_id, sent_at);
CREATE INDEX idx_nudge_delivery_log_user_level ON nudge_delivery_log (user_id, nudge_level);

CREATE TABLE nudge_engagement (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    last_engagement_at TIMESTAMPTZ,
    paused_until TIMESTAMPTZ,
    total_nudges_sent INTEGER DEFAULT 0,
    total_acted_on INTEGER DEFAULT 0,
    UNIQUE (user_id, pet_id)
);

CREATE TABLE nudge_message_library (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    level INTEGER NOT NULL,
    slot_day INTEGER NOT NULL DEFAULT 0,
    seq INTEGER NOT NULL DEFAULT 1,
    message_type VARCHAR(30) NOT NULL,
    breed VARCHAR(100) NOT NULL DEFAULT 'All',
    category VARCHAR(50),
    template_key VARCHAR(100) NOT NULL,
    template_var_1 TEXT,
    template_var_2 TEXT,
    template_var_3 TEXT,
    template_var_4 TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_nudge_level CHECK (level IN (0,1,2)),
    CONSTRAINT chk_message_type CHECK (message_type IN ('value_add','engagement_only','breed_only','breed_data')),
    UNIQUE (level, slot_day, seq, message_type, breed)
);

CREATE INDEX idx_nudge_library_level_slot ON nudge_message_library (level, slot_day, message_type, breed);
CREATE INDEX idx_nudge_library_l2_category ON nudge_message_library (level, category, breed) WHERE level = 2;

CREATE TABLE breed_consequence_library (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    breed VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    consequence_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (breed, category)
);

CREATE INDEX idx_breed_consequence_breed_category ON breed_consequence_library (breed, category);

-- ============================================================================
-- 14. WHATSAPP & MESSAGING TABLES
-- ============================================================================

CREATE TABLE whatsapp_template_configs (
    template_name VARCHAR(100) PRIMARY KEY,
    body_text TEXT NOT NULL DEFAULT '',
    param_count INTEGER NOT NULL DEFAULT 0,
    language_code VARCHAR(10) NOT NULL DEFAULT 'en',
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE message_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    pet_id UUID REFERENCES pets(id),
    message_type VARCHAR(50),
    content TEXT,
    status VARCHAR(20),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 15. FOREIGN KEY CONSTRAINT FOR users.active_reminder_id (added after reminders table)
-- ============================================================================

ALTER TABLE users
    ADD CONSTRAINT fk_users_active_reminder_id
    FOREIGN KEY (active_reminder_id)
    REFERENCES reminders(id) ON DELETE SET NULL;

-- ============================================================================
-- COMMIT
-- ============================================================================

COMMIT;
