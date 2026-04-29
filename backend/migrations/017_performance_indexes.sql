-- Migration 017: Add performance indexes for dashboard queries
-- Composite indexes on high-frequency filter patterns used in dashboard_service.py

-- PreventiveRecord: filtered by pet_id + status in health score, care plan, and overdue calculations
CREATE INDEX IF NOT EXISTS idx_preventive_record_pet_status
ON preventive_records(pet_id, status);

-- PreventiveRecord: filtered by pet_id ordered by next_due_date for upcoming/overdue queries
CREATE INDEX IF NOT EXISTS idx_preventive_record_pet_next_due
ON preventive_records(pet_id, next_due_date);

-- Condition: filtered by pet_id + is_active for active conditions tab and health score
CREATE INDEX IF NOT EXISTS idx_condition_pet_active
ON conditions(pet_id, is_active);

-- WeightHistory: filtered by pet_id ordered by recorded_at for weight trend analysis
CREATE INDEX IF NOT EXISTS idx_weight_history_pet_date
ON weight_history(pet_id, recorded_at DESC);

-- DiagnosticTestResult: filtered by pet_id + test_type for diagnostics tab
CREATE INDEX IF NOT EXISTS idx_diagnostic_test_result_pet_type
ON diagnostic_test_results(pet_id, test_type);

-- Document: filtered by pet_id + extraction_status for pending documents
CREATE INDEX IF NOT EXISTS idx_document_pet_extraction_status
ON documents(pet_id, extraction_status);

-- Reminder: filtered by pet_id + status for reminder dashboard and deduplication
CREATE INDEX IF NOT EXISTS idx_reminder_pet_status
ON reminders(pet_id, status);

-- ConditionMedication: filtered by condition_id for medications tab
CREATE INDEX IF NOT EXISTS idx_condition_medication_condition_id
ON condition_medications(condition_id);

-- ConditionMonitoring: filtered by condition_id for monitoring items tab
CREATE INDEX IF NOT EXISTS idx_condition_monitoring_condition_id
ON condition_monitoring(condition_id);

-- CartItem: filtered by pet_id for cart retrieval (no user_id column; keyed by pet_id + product_id)
CREATE INDEX IF NOT EXISTS idx_cart_item_pet_id
ON cart_items(pet_id);
