-- Migration 024: Add reminder_config table
-- Purpose: DB-configurable reminder engine settings (snooze days, rate limits, send times).
--          Mirrors the nudge_config pattern. Constants in code remain as fallback defaults.

CREATE TABLE IF NOT EXISTS reminder_config (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key         VARCHAR(100) UNIQUE NOT NULL,
    value       VARCHAR(200) NOT NULL,
    description TEXT,
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Seed: snooze intervals (days to push next_due_date forward on snooze)
INSERT INTO reminder_config (key, value, description) VALUES
    ('snooze_days_vaccine',      '7',  'Days to snooze vaccine reminders'),
    ('snooze_days_deworming',    '7',  'Days to snooze deworming reminders'),
    ('snooze_days_flea',         '7',  'Days to snooze flea/tick reminders'),
    ('snooze_days_food',         '7',  'Days to snooze food-order reminders'),
    ('snooze_days_supplement',   '7',  'Days to snooze supplement reminders'),
    ('snooze_days_medicine',     '7',  'Days to snooze medicine reminders'),
    ('snooze_days_vet_followup', '7',  'Days to snooze vet-followup reminders'),
    ('snooze_days_hygiene',      '7',  'Days to snooze hygiene reminders')
ON CONFLICT (key) DO NOTHING;

-- Seed: rate-limit / spacing thresholds
INSERT INTO reminder_config (key, value, description) VALUES
    ('max_reminders_per_pet_per_day',        '1',  'Max reminders sent to a single pet in one day'),
    ('min_days_between_same_item_reminders', '3',  'Min days between sends for the same preventive item'),
    ('reminder_ignore_threshold',            '3',  'Ignored-reminder count before monthly-only fallback'),
    ('reminder_monthly_interval_days',       '30', 'Days between monthly overdue_insight repeats'),
    ('reminder_min_gap_days',                '3',  'Min days between any two reminders for the same pet')
ON CONFLICT (key) DO NOTHING;

-- Seed: send times (IST, HH:MM format)
INSERT INTO reminder_config (key, value, description) VALUES
    ('send_time_t7',          '09:00', 'Send time (IST) for T-7 stage reminders'),
    ('send_time_due',         '10:00', 'Send time (IST) for due-date reminders'),
    ('send_time_d3',          '09:00', 'Send time (IST) for D+3 overdue reminders'),
    ('send_time_overdue',     '09:00', 'Send time (IST) for overdue_insight reminders'),
    ('send_time_hygiene_due', '10:00', 'Send time (IST) for hygiene due reminders')
ON CONFLICT (key) DO NOTHING;
