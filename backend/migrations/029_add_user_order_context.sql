-- Migration 029: Add order_context JSONB column to users table
-- Stores in-progress order conversation state (pet_id, sku_options, etc.)
-- Complements the existing order_state column.

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS order_context JSONB;
