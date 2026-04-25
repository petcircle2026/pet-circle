-- PetCircle Migration 023 — Drop Unused Columns
-- Date: 2026-04-25
-- Purpose: Remove write-only and superseded columns from production schema

-- ============================================================================
-- NUDGE TABLE: Drop WA Tracking Columns
-- These three columns were used by an older nudge design where WA tracking
-- was stored directly on the nudges table. When the system was refactored,
-- tracking was moved to nudge_delivery_log, which has its own wa_status,
-- template_name, and message_body columns. These columns have been superseded.
-- ============================================================================

ALTER TABLE nudges DROP COLUMN IF EXISTS wa_status;
-- REASON: Tracking moved to nudge_delivery_log.wa_status

ALTER TABLE nudges DROP COLUMN IF EXISTS wa_sent_at;
-- REASON: Timestamp tracking moved to nudge_delivery_log.created_at

ALTER TABLE nudges DROP COLUMN IF EXISTS wa_message_id;
-- REASON: Message ID tracking moved to nudge_delivery_log (unused, replaced by proper delivery logs)

-- ============================================================================
-- DOCUMENTATION: Write-Only Columns (Not Dropped)
-- ============================================================================

-- preventive_records.vaccination_metadata — WRITE-ONLY, RETAINED
-- This JSONB column is written by gpt_extraction.py (rich vaccine metadata: dose,
-- route, batch_number, manufacturer, administered_by) but never read by any service
-- or router. Kept for potential future use (e.g., vaccine batch tracking, adverse event
-- correlation). If removed in the future, the extracted data should first be migrated
-- to a proper vaccination_details table.
COMMENT ON COLUMN preventive_records.vaccination_metadata IS
  'Write-only: populated by GPT extraction with vaccine details (dose, route, batch, etc).
   No read path exists yet. Retained for future use (e.g. batch tracking, AE correlation).';

-- nudge_config.description — ANNOTATION COLUMN, RETAINED
-- Populated at seed time with operator-friendly descriptions of config keys.
-- Never queried at runtime, but useful for ops debugging and manual config audits.

-- nudge_message_library.notes — ANNOTATION COLUMN, RETAINED
-- Populated at seed time with content-team annotations. Never queried at runtime,
-- but useful for editorial tracking and message provenance audits.
